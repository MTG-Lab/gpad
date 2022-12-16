'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Monday, March 22nd 2021, 11:58:34 am
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''

import logging
import re
import pendulum
from datetime import date, timedelta, datetime

import click
import spacy
from dateutil import parser
from spacy.matcher import DependencyMatcher, PhraseMatcher
from tqdm import tqdm, trange
from word2number import w2n
from mongoengine.queryset.visitor import Q

from .models import *
from .settings import *



class Curator:
    INF = 99999
    ignore_before = 1980
    publication_regex = r"([0-9]{1,}):([a-zA-Z' \-]{3,}\.?),?\ [\(]?([0-9]{4})[\)]?"
    date_regex = r"^\d{1,2}\/\d{1,2}\/\d{4}$"
    animal_models = [
        "Saccharomyces cerevisiae", "S. cerevisiae", "Yeast",
        "Pisum sativum", "Pea plant",
        "Drosophila melanogaster", "D. melanogaster", "Drosophila", "Fruit fly",
        "Caenorhabditis elegans", "C. elegans", "Roundworm", "worm", "worms",
        "Danio rerio", "Zebra fish", "zebrafish",
        "Mus musculus", "mouse", "mice",
        "Rattus norvegicus", "rat", "rats", "rodent", "avian", "Xenopus", "cattle", "bull", "chicken", "dog"
    ]  # TODO: Plural forms
    ignore_phenotypes = ['[', '{', '?', 'susceptibility', 'modifier']
    phenotype_inheritence_types = [
        'Autosomal dominant', 'Autosomal recessive', 'Pseudoautosomal dominant', 'Pseudoautosomal recessive',
        'X-linked', 'X-linked dominant', 'X-linked recessive', 'Y-linked']
    matcher_platform = ["GeneMatcher", "Matchmaker", "DECIPHER",
                        "IRUD", "MyGene2", "PatientMatcher", "PhenomeCentral", ]
    cohort_phrase_pattern = [
        {
            "RIGHT_ID": "anchor_patients",
            "RIGHT_ATTRS": {"LEMMA": {"IN": ["family", "patient", "child", "boy", "girl", "parent", "individual", "people", "infant", "woman", "man"]}, "POS": "NOUN"}
        },
        {
            "LEFT_ID": "anchor_patients",
            "REL_OP": ">",
            "RIGHT_ID": "patient_modifier",
            "RIGHT_ATTRS": {"LEMMA": {"IN": ["independent", "separate", "unrelated", "more", "different", "new", "sporadic", "further", "additional", "other"]},
                            "DEP": "amod", "POS": "ADJ",
                            "ENT_TYPE": {"NOT_IN": ["NORP"], }}
        },
        {
            "LEFT_ID": "anchor_patients",
            "REL_OP": ">",
            "RIGHT_ID": "patient_count",
            "RIGHT_ATTRS": {"LIKE_NUM": True, "DEP": "nummod", "POS": "NUM"},
        },
    ]


    original_study_pattern = [
        {
            "RIGHT_ID": "anchor_verb",
            "RIGHT_ATTRS": {"POS": "VERB"}  # "LEMMA": {"IN": ["describe", "report", "study", "diagnose", "find"]},
        },
        {
            "LEFT_ID": "anchor_verb",
            "REL_OP": ">",
            "RIGHT_ID": "origin_modifier",
            # "LEMMA": {"IN": ["originally", "previously"]},
            "RIGHT_ATTRS": {"POS": "ADV", "DEP": "advmod", "LEMMA": {"NOT_IN": ["later", "recent"]}}
        },
        {
            "LEFT_ID": "anchor_verb",
            "REL_OP": ">",
            "RIGHT_ID": "agent_modifier",
            "RIGHT_ATTRS": {"POS": "ADP", "DEP": "agent"}
        },
        {
            "LEFT_ID": "agent_modifier",
            "REL_OP": ">",
            "RIGHT_ID": "agent",
            "RIGHT_ATTRS": {"LIKE_NUM": True, "DEP": "pobj", "POS": "NUM"},
        },
    ]
    
    
    def __init__(self) -> None:
        # text_variations = {}
        # Defining NLP matchers
        self.nlp = spacy.load("en_core_web_sm")
        self.dependency_matcher = DependencyMatcher(self.nlp.vocab)
        self.dependency_matcher.add("Patient", [self.cohort_phrase_pattern])
        # Original Study Matcher
        self.original_study_matcher = DependencyMatcher(self.nlp.vocab)
        self.original_study_matcher.add("OriginalStudy", [self.original_study_pattern])
        # Animal Matcher
        self.animal_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self.patterns = [self.nlp.make_doc(a) for a in self.animal_models]
        self.animal_matcher.add("Animal", self.patterns)
        # Gene matcher platforms
        self.matcher_platform_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self.patterns = [self.nlp.make_doc(a) for a in self.matcher_platform]
        self.matcher_platform_matcher.add("Platform", self.patterns)


    def __original_study_finder(self, doc):
        original_study_matches = self.original_study_matcher(doc)
        pub_ref_ids = []
        if original_study_matches:
            for match_id, token_ids in original_study_matches:
                pub_ref_ids.append(doc[token_ids[3]].text)
                # for i in range(len(token_ids)):
                #     # print(original_study_pattern[i]["RIGHT_ID"] + ":", doc[token_ids[i]].text)
                #     if original_study_pattern[i]["RIGHT_ID"] not in text_variations:
                #         text_variations[original_study_pattern[i]["RIGHT_ID"]] = []
                #     text_variations[original_study_pattern[i]["RIGHT_ID"]].append(doc[token_ids[i]].text)
        return pub_ref_ids


    def __nearest_publication_detector(self, text, ref_start_position):
        """Detect nearest citation from the anchor token

        Args:
            text (str): Text to look through
            ref_start_position (int): anchor token position

        Returns:
            Match: publication Match object
        """
        text = text.replace('al.', 'al')
        doc = self.nlp(text)
        pub_ref_ids = self.__original_study_finder(doc)
        
        # All citation in the text
        publication_matches = re.finditer(self.publication_regex, text)
        nearest_match = None
        lowest_distance = self.INF
        for match in publication_matches:
            distance = self.INF
            # Detect same sentence publications and take the latest one.
            sentence = doc.char_span(match.start(0), match.end(0), alignment_mode='expand').sent.text
            same_sentence_pubs = re.finditer(self.publication_regex, sentence)
            if same_sentence_pubs:
                for proximal_match in same_sentence_pubs:
                    if int(proximal_match.group(3)) > int(match.group(3)):
                        logging.debug(
                            f"{proximal_match.group(3)} > {match.group(3)} = {proximal_match.group(3) > match.group(3)}")
                        match = proximal_match
            # Ignore if it is found as part of "original" patient reporting study
            if (pub_ref_ids and match.group(1) in pub_ref_ids):
                continue
            # Consider proximity of the detected publication to the anchor text
            if match.start(0) < ref_start_position:
                distance = abs(ref_start_position - match.start(0))
            elif nearest_match is None and match.start(0) > ref_start_position:
                distance = abs(match.start(0) - ref_start_position)
            if distance < lowest_distance:
                nearest_match = match
                lowest_distance = distance
        return nearest_match


    def __create_publication_object_from_match(self, pub_match, reference_list=None):
        pmid = None
        if reference_list:
            for ref in reference_list:
                # print(pub_match)
                if 'referenceNumber' in ref['reference'] \
                        and ref['reference']['referenceNumber'] == int(pub_match.group(1)) \
                        and 'pubmedID' in ref['reference']:
                    pmid = ref['reference']['pubmedID']
        # print(pub_match.group(0))
        pub = PublicationItem()
        pub["pmid"] = pmid
        pub["author"] = pub_match.group(2)
        pub["year"] = pub_match.group(3)
        return pub


    def __get_matcher_platform(self, text, reference_list=None):
        matcher_platforms = []
        doc = self.nlp(text)
        matches = self.matcher_platform_matcher(doc)
        if matches:
            for match_id, start, end in matches:
                nearest_pub = self.__nearest_publication_detector(
                    doc.text, doc[start:end].start_char)
                if nearest_pub:
                    matcher_platform = MatcherPlatform()
                    matcher_platform['platform_name'] = doc[start:end].text
                    matcher_platform['publication_evidence'] = self.__create_publication_object_from_match(
                        nearest_pub, reference_list)
                    if matcher_platform not in matcher_platforms:
                        matcher_platforms.append(
                            matcher_platform)
        return matcher_platforms


    def __get_animal_model(self, text, reference_list=None):
        animal_models = []
        # Detecting animal model
        doc = self.nlp(text)
        matches = self.animal_matcher(doc)
        if matches:
            for match_id, start, end in matches:
                nearest_pub = self.__nearest_publication_detector(
                    doc.text, doc[start:end].start_char)
                if nearest_pub:
                    animal_model = AnimalModelsItem()
                    animal_model['animal_name'] = doc[start:end].text
                    # print(f"========\n{doc.text}\n{nearest_pub}=======")
                    animal_model['publication_evidence'] = self.__create_publication_object_from_match(
                        nearest_pub, reference_list)
                    if animal_model not in animal_models:
                        animal_models.append(animal_model)
        return animal_models


    def __get_cohorts(self, text, reference_list=None, source='gene'):
        # print("cohort start")
        # Detecting patient information
        cohorts = []
        doc = self.nlp(text)          # TODO: Also detect population here? making it attachable to the cohort info
        patient_matches = self.dependency_matcher(doc)
        if patient_matches:
            match_ids = []
            for match_id, token_ids in patient_matches:
                if match_id not in match_ids:
                    cohort = CohortDescription()
                    cohort['source'] = source
                    for i in range(len(token_ids)):
                        if self.cohort_phrase_pattern[i]["RIGHT_ID"] == 'anchor_patients':
                            cohort['cohort_type'] = doc[token_ids[i]].text
                        if self.cohort_phrase_pattern[i]["RIGHT_ID"] == 'patient_modifier':
                            cohort['cohort_relation'] = doc[token_ids[i]].text
                        if self.cohort_phrase_pattern[i]["RIGHT_ID"] == 'patient_count':
                            try:
                                cohort['cohort_count'] = w2n.word_to_num(doc[token_ids[i]].text)
                            except:
                                cohort['cohort_count'] = -1
                                # logging.warning(doc[token_ids[i]].text)
                    nearest_pub = self.__nearest_publication_detector(
                        doc.text, doc[token_ids[0]:token_ids[1]].start_char)
                    if nearest_pub:
                        cohort['publication_evidence'] = self.__create_publication_object_from_match(
                            nearest_pub, reference_list)
                    cohorts.append(cohort)
                    match_ids.append(match_id)
        # print("cohort end")
        return cohorts


    def extract_and_save(self, entry, item):
        item['_id'] = entry._id
        item["gene_mim_id"] = entry.mimNumber
        item['prefix'] = entry.prefix
        if 'geneMap' in entry and 'geneSymbols' in entry.geneMap:
            item["gene_symbols"] = entry.geneMap['geneSymbols']
        if 'geneMap' in entry and 'geneName' in entry.geneMap:
            item["gene_name"] = entry.geneMap['geneName']
        # print(entry.mimNumber)
        item["date_created"] = entry.dateCreated
        item["date_updated"] = entry.dateUpdated
        item["mtg_created"] = entry.mtgCreated
        item["mtg_updated"] = datetime.now()
        item["edit_history"] = []
        # TODO: change to regex
        edit_history = self.nlp(entry.editHistory.replace('\n', ' '))
        for ent in edit_history.ents:
            if ent.label_ == 'DATE':
                edit_date = re.match(self.date_regex, ent.text)
                if edit_date:
                    item["edit_history"].append(
                        str(parser.parse(edit_date.group())))

        var_pheno_assoc = []
        organism_used = []
        matcher_platforms = []

        # Known Genotype-Phenotype relationships
        phenos = []
        _known_phenos = []
        # TODOS
        # ADD PREFIX FILTER
        ##
        if entry.geneMap is not None and 'phenotypeMapList' in entry.geneMap:
            known_phenotypes = entry.geneMap['phenotypeMapList']
            for p in known_phenotypes:
                phenotype_check = False
                animal_models = []
                pubs = []
                allelic_variants = []
                population = []
                cohorts = []
                if 'phenotypeInheritance' in p['phenotypeMap'] \
                        and 'phenotype' in p['phenotypeMap'] and p['phenotypeMap']['phenotype'] \
                        and p['phenotypeMap']['phenotypeInheritance']:
                    phenotype_name = p['phenotypeMap']['phenotype']
                    inheritance = p['phenotypeMap']['phenotypeInheritance']
                    # Check if type of inheritance is Mendelian
                    pits = inheritance.split(';')
                    for pit in pits:
                        # for pit.strip() in phenotype_inheritence_types:
                        if pit.strip() in self.phenotype_inheritence_types:
                            phenotype_check = True
                            break
                        # if phenotype_check:
                        #     break
                    # Check if there is a clear association
                    for ip in self.ignore_phenotypes:
                        if ip in phenotype_name:
                            phenotype_check = False
                            break
                    if phenotype_check:
                        pheno = Phenotype()
                        pheno_mim = None
                        if 'phenotype' in p['phenotypeMap']:
                            pheno['phenotype'] = phenotype_name
                        if 'phenotypeMimNumber' in p['phenotypeMap']:
                            pheno_mim = p['phenotypeMap']['phenotypeMimNumber']
                            pheno['mim_number'] = pheno_mim
                            _known_phenos.append(pheno_mim)
                        if 'phenotypeMappingKey' in p['phenotypeMap']:
                            pheno['mapping_key'] = p['phenotypeMap']['phenotypeMappingKey']
                            # Look at the phenotype for extractable information
                            pheno_entry = GeneEntry.objects(
                                mimNumber=pheno_mim).first()
                            if pheno_entry:
                                pheno['prefix'] = pheno_entry['prefix']

                                # Detecting matcher platform from the phenotype entry
                                # NOTE: Might not be good for genetically heterogenious phenotypes
                                pheno_text = ' '.join(t['textSection']['textSectionContent'].replace(
                                    '\n\n', ' ') for t in pheno_entry.textSectionList)

                                cohorts = self.__get_cohorts(pheno_text, pheno_entry.referenceList, source="phenotype")

                                _matcher_platforms = self.__get_matcher_platform(pheno_text, pheno_entry.referenceList)
                                for m in _matcher_platforms:
                                    if m not in matcher_platforms:
                                        matcher_platforms.append(m)

                                # Detecting animal model
                                for pheno_text in pheno_entry.textSectionList:
                                    if pheno_text['textSection']['textSectionName'] == 'animalModel':
                                        anim_paras = pheno_text['textSection']['textSectionContent'].split(
                                            '\n\n')
                                        for p in anim_paras:
                                            _animal_models = self.__get_animal_model(p, pheno_entry.referenceList)
                                            for animal_model in _animal_models:
                                                if animal_model not in animal_models:
                                                    animal_models.append(animal_model)
                                                if animal_model not in organism_used:
                                                    organism_used.append(animal_model)
                                    # Looking at Molecular Genetics excerpt
                                    if pheno_text['textSection']['textSectionName'] == 'molecularGenetics':
                                        mol_gen_paras = text['textSection']['textSectionContent'].split(
                                            '\n\n')
                                        mol_gen_flag = None
                                        pubs = []
                                        population = []
                                        _phenos = []
                                        for p in mol_gen_paras:
                                            doc = self.nlp(p)
                                            # Detecting populations
                                            for ent in doc.ents:
                                                if ent.label_ == 'NORP':
                                                    population.append(ent.text)
                                            for kp in _known_phenos:
                                                if str(kp) in p:
                                                    _phenos.append(kp)
                                            # Detecting publication evidence
                                            publication_matches = re.finditer(publication_regex, p)
                                            for pub_match in publication_matches:
                                                pub = create_publication_object_from_match(pub_match, entry.referenceList)
                                                if pub not in pubs:
                                                    pubs.append(pub)
                                            if '<Subhead>' in p:
                                                if mol_gen_flag is not None or len(pubs) > 0:
                                                    mol_gen = MolGenItem()
                                                    mol_gen["section_title"] = mol_gen_flag
                                                    mol_gen["referred_entry"] = _phenos
                                                    mol_gen["publication_evidence"] = pubs
                                                    mol_gen["populations"] = list(set(population))
                                                    var_pheno_assoc.append(mol_gen)
                                                mol_gen_flag = p.replace('<Subhead>', '').strip()
                                                pubs = []
                                                population = []
                                        if mol_gen_flag is None and len(pubs) > 0:
                                            mol_gen = MolGenItem()
                                            mol_gen["section_title"] = mol_gen_flag
                                            mol_gen["referred_entry"] = _phenos
                                            mol_gen["publication_evidence"] = pubs
                                            mol_gen["populations"] = list(set(population))
                                            var_pheno_assoc.append(mol_gen)
                                
                        # Check Allelic variants' text for the gene
                        for allele in entry.allelicVariantList:
                            if 'text' in allele['allelicVariant']:
                                text = allele['allelicVariant']['text'].replace(
                                    '\n\n', ' ')
                                text = text.replace('al.', 'al')

                                # TODO: Combine same phenotype variants for gene level detection?
                                if str(pheno_mim) in text:
                                    if 'name' in allele['allelicVariant']:
                                        av = AllelicVariant()
                                        av['name'] = allele['allelicVariant']['name']

                                    doc = self.nlp(text)
                                    # Detecting cohort descriptoion
                                    _cohorts = self.__get_cohorts(text, entry.referenceList, source="gene")
                                    for _c in _cohorts:
                                        if _c not in cohorts:
                                            cohorts.append(_c)
                                    av['cohorts'] = _cohorts

                                    # Detecting matcher platform from gene entry
                                    _matcher_platforms = self.__get_matcher_platform(text, entry.referenceList)
                                    for m in _matcher_platforms:
                                        if m not in matcher_platforms:
                                            matcher_platforms.append(m)
                                    av['matcher_platforms'] = _matcher_platforms

                                    # Detecting populations
                                    for ent in doc.ents:
                                        if ent.label_ == 'NORP':
                                            population.append(ent.text)

                                    # Detecting publication evidence
                                    av['publication_evidences'] = []
                                    pub_ref_ids = self.__original_study_finder(doc)
                                    publication_matches = re.finditer(self.publication_regex, text)
                                    for pub_match in publication_matches:
                                        sentence = doc.char_span(pub_match.start(0), pub_match.end(0),
                                                                alignment_mode='expand').sent.text
                                        same_sentence_pubs = re.finditer(self.publication_regex, sentence)
                                        if same_sentence_pubs:
                                            # print(sentence)
                                            for proximal_match in same_sentence_pubs:
                                                if proximal_match.group(3) > pub_match.group(3):
                                                    pub_match = proximal_match
                                                # print(proximal_match)
                                        if pub_ref_ids and pub_match.group(1) in pub_ref_ids:
                                            continue
                                        pub = self.__create_publication_object_from_match(pub_match, entry.referenceList)
                                        if pub not in pubs:
                                            pubs.append(pub)
                                        if pub not in av['publication_evidences']:
                                            av['publication_evidences'].append(pub)

                                    # Detecting animal model
                                    av['animal_models'] = []
                                    _animal_models = self.__get_animal_model(text, entry.referenceList)
                                    for animal_model in _animal_models:
                                        if animal_model not in animal_models:
                                            animal_models.append(animal_model)
                                        if animal_model not in organism_used:
                                            organism_used.append(animal_model)
                                        if animal_model not in av['animal_models']:
                                            av['animal_models'].append(animal_model)
                                    allelic_variants.append(av)

                        if allelic_variants:
                            pheno['allelic_variants'] = allelic_variants
                        if pubs:
                            pheno['publication_evidences'] = pubs
                        if population:
                            pheno['populations'] = list(set(population))
                        if cohorts:
                            pheno['cohorts'] = cohorts
                        if animal_models:
                            pheno['animal_models'] = animal_models
                        if matcher_platforms:
                            pheno['matcher_platforms'] = matcher_platforms
                        phenos.append(pheno)

        item["phenotypes"] = phenos

        if entry.textSectionList:
            texts = entry.textSectionList
            for text in texts:
                # Looking at Molecular Genetics excerpt
                if text['textSection']['textSectionName'] == 'molecularGenetics':
                    mol_gen_paras = text['textSection']['textSectionContent'].split(
                        '\n\n')
                    mol_gen_flag = None
                    pubs = []
                    population = []
                    _phenos = []
                    # for p in mol_gen_paras:
                    #     doc = self.nlp(p)
                    #     # Detecting populations
                    #     for ent in doc.ents:
                    #         if ent.label_ == 'NORP':
                    #             population.append(ent.text)
                    #     for kp in _known_phenos:
                    #         if str(kp) in p:
                    #             _phenos.append(kp)
                    #     # Detecting publication evidence
                    #     publication_matches = re.finditer(self.publication_regex, p)
                    #     for pub_match in publication_matches:
                    #         pub = self.__create_publication_object_from_match(pub_match, entry.referenceList)
                    #         if pub not in pubs:
                    #             pubs.append(pub)
                    #     if '<Subhead>' in p:
                    #         if mol_gen_flag is not None or len(pubs) > 0:
                    #             mol_gen = MolGenItem()
                    #             mol_gen["section_title"] = mol_gen_flag
                    #             mol_gen["referred_entry"] = _phenos
                    #             mol_gen["publication_evidence"] = pubs
                    #             mol_gen["populations"] = list(set(population))
                    #             var_pheno_assoc.append(mol_gen)
                    #         mol_gen_flag = p.replace('<Subhead>', '').strip()
                    #         pubs = []
                    #         population = []
                    # if mol_gen_flag is None and len(pubs) > 0:
                    #     mol_gen = MolGenItem()
                    #     mol_gen["section_title"] = mol_gen_flag
                    #     mol_gen["referred_entry"] = _phenos
                    #     mol_gen["publication_evidence"] = pubs
                    #     mol_gen["populations"] = list(set(population))
                    #     var_pheno_assoc.append(mol_gen)
                # Looking at Animal Model excerpt
                if text['textSection']['textSectionName'] == 'animalModel':
                    anim_paras = text['textSection']['textSectionContent'].split(
                        '\n\n')
                    for p in anim_paras:
                        _animal_models = self.__get_animal_model(p, entry.referenceList)
                        for animal_model in _animal_models:
                            if animal_model not in organism_used:
                                organism_used.append(animal_model)

        item["molecular_genetics"] = var_pheno_assoc
        item["animal_models"] = organism_used
        item.save()


    def curate(self, mims_to_curate):
        entries = None
        if len(mims_to_curate):
            entries = GeneEntry.objects(mimNumber__in=mims_to_curate)
        else:
            gms = GeneMap.objects
            mims = [int(_e.mimNumber) for _e in gms]
            entries = GeneEntry.objects(mimNumber__in=mims)
        for entry in tqdm(entries, desc="Applying NLP!"):
            curated_gene_info = CuratedGeneInfo.objects(_id=entry._id).only('_id')
            if curated_gene_info.count() == 0:
                item = CuratedGeneInfo()
                self.extract_and_save(entry, item)
