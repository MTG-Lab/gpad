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
from Bio import Entrez

from .models import *
from .settings import *


class Curator:
    INF = 99999
    ignore_before = 1980
    max_cohort_size = 3000
    pubmed_date_regex = r"(\d{4})\ ?(\S{3})?( \d{2})?"
    publication_regex = r"([0-9]{1,}):([a-zA-Z0-9' \/-]{3,}\.?),?\ [\(]?([0-9]{4})[\)]?"
    publication_mask = r"\{REF#([0-9]{1,})\}"
    date_regex = r"^\d{1,2}\/\d{1,2}\/\d{4}$"
    determinant = ["a", "an"]
    detection_modules = ['basic','association','animal','cohort']
    animal_models = [
        "Saccharomyces cerevisiae", "S. cerevisiae", "Yeast",
        "Pisum sativum", "Pea plant",
        "Drosophila melanogaster", "D. melanogaster", "Drosophila", "Fruit fly",
        "Caenorhabditis elegans", "C. elegans", "Roundworm", "worm", "worms",
        "Danio rerio", "Zebra fish", "zebrafish",
        "Mus musculus", "mouse", "mice",
        "Rattus norvegicus", "rat", "rats", "rodent", "avian", "Xenopus", "cattle", "bull", "chicken", "dog"
    ]
    animal_model_types = {
        "Yeast": ["Saccharomyces cerevisiae", "S. cerevisiae", "Yeast"],
        "Drosophila": ["Drosophila melanogaster", "D. melanogaster", "Drosophila", "Fruit fly"],
        "C. elegans": ["Caenorhabditis elegans", "C. elegans", "Roundworm", "worm", "worms"],
        "Zebrafish": ["Danio rerio", "Zebra fish", "zebrafish"],
        "Mouse": ["Mus musculus", "mouse", "mice"],
        "Rat": ["Rattus norvegicus", "rat", "rats", "rodent"],
        "Others": ["Pisum sativum", "Pea plant", "avian", "Xenopus", "cattle", "bull", "chicken", "dog"]
    }
    ignore_phenotypes = ['[', '{', '?', 'susceptibility', 'modifier']
    phenotype_inheritence_types = [
        'Autosomal dominant', 'Autosomal recessive', 'Pseudoautosomal dominant', 'Pseudoautosomal recessive',
        'X-linked', 'X-linked dominant', 'X-linked recessive', 'Y-linked']
    matcher_platform = ["GeneMatcher", "Matchmaker", "DECIPHER",
                        "IRUD", "MyGene2", "PatientMatcher", "PhenomeCentral", ]
    
    cohort_pattern = {
        "cohort_pattern": [
            {
                "RIGHT_ID": "anchor_patients",
                "RIGHT_ATTRS": {"LEMMA": {"IN": ["family", "patient", "child", "boy", "girl", "parent", "individual", "member", "people", "infant", "woman", "man"]}, "POS": "NOUN"}
            },
            {
                "LEFT_ID": "anchor_patients",
                "REL_OP": ">",
                "RIGHT_ID": "patient_modifier",
                "RIGHT_ATTRS": {"LEMMA": {"IN": ["independent", "separate", "unrelated", "more", "different", "new", "sporadic", "further", "additional", "other", "affected"]},
                                "DEP": "amod", "POS": "ADJ",
                                "ENT_TYPE": {"NOT_IN": ["NORP"], }}
            },
            {
                "LEFT_ID": "anchor_patients",
                "REL_OP": ">",
                "RIGHT_ID": "patient_count",
                "RIGHT_ATTRS": {"LIKE_NUM": True, "DEP": "nummod", "POS": "NUM"},
            },
        ],
        "cohort_with_det": [
                {
                    "RIGHT_ID": "anchor_patients",
                    "RIGHT_ATTRS": {"LEMMA": {"IN": ["family", "patient", "child", "boy", "girl", "parent", "individual", "affected", "people", "infant", "woman", "man"]}, "POS": "NOUN"}
                },
                {
                    "LEFT_ID": "anchor_patients",
                    "REL_OP": ">",
                    "RIGHT_ID": "patient_count",
                    "RIGHT_ATTRS": {"DEP": "det", "POS": "DET", "LEMMA": {"IN": ["a", "an"]}},
                },
        ]
    }
    # cohort_phrase_pattern = [
    #     {
    #         "RIGHT_ID": "anchor_patients",
    #         "RIGHT_ATTRS": {"LEMMA": {"IN": ["family", "patient", "child", "boy", "girl", "parent", "individual", "people", "infant", "woman", "man", "proband", "case"]}, "POS": "NOUN"}
    #     },
    #     {
    #         "LEFT_ID": "anchor_patients",
    #         "REL_OP": ">",
    #         "RIGHT_ID": "patient_count",
    #         "RIGHT_ATTRS": {"LIKE_NUM": True, "DEP": "nummod", "POS": "NUM"},
    #     },
    # ]
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
        # Cohort
        self.cohort_matcher = DependencyMatcher(self.nlp.vocab)
        self.cohort_matcher.add("Cohort", [self.cohort_pattern["cohort_pattern"]])
        self.cohort_matcher.add("CohortDet", [self.cohort_pattern["cohort_with_det"]])
        # Unrelated Patient
        # self.unrelated_cohort_matcher = DependencyMatcher(self.nlp.vocab)
        # self.unrelated_cohort_matcher.add("UnrelatedCohort", [self.unrelated_cohort_phrase_pattern])
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
                # logging.debug(doc[token_ids[3]].text)
                pub_ref_ids.append(doc[token_ids[3]].text)
        return pub_ref_ids
    
    def __mask_citation(match):
        return "Ref#" + match.group(1)
    
    
    def __get_pubmed_entry(self, pmid):
        """Get publication date from pubmed ID

        Args:
            pmid (int): Pubmed PMID

        Returns:
            str: date wit month information
        """
        pe = None
        if pmid:
            pe = PubmedEntry.objects(pmid=pmid).first()
            if pe == None:
                logging.info(f"Sending Entrez request for PMID: {pmid}")
                pe = PubmedEntry()
                handle = Entrez.esummary(db="pubmed", id=pmid)
                record = Entrez.read(handle)
                handle.close()
                logging.debug(record)
                pe.pmid = pmid
                pe.raw_pub_date = record[0]["PubDate"]
                dt_match = re.match(self.pubmed_date_regex, record[0]["PubDate"])
                try:
                    if dt_match and dt_match.group(3):
                        pe.pub_date =  datetime.strptime(dt_match.group(), "%Y %b %d")
                    elif dt_match:
                        pe.pub_date =  datetime.strptime(dt_match.group(), "%Y %b")
                except ValueError as e:
                    logging.exception(repr(e))
                if dt_match:
                    pe.pub_year = dt_match.group(1)
                
                if 'EPubDate' in record[0]:
                    pe.raw_epub_date = record[0]["EPubDate"]
                    epub_dt_match = re.match(self.pubmed_date_regex, record[0]["EPubDate"])                
                    if epub_dt_match:
                        if epub_dt_match.group(1):
                            pe.pub_year = epub_dt_match.group(1)
                        if epub_dt_match.group(3):
                            pe.epub_date =  datetime.strptime(epub_dt_match.group(), "%Y %b %d")
                        elif epub_dt_match:
                            pe.epub_date =  datetime.strptime(epub_dt_match.group(), "%Y %b")
                        
                # Journal name
                if 'FullJournalName' in record[0]:
                    pe.journal_name = record[0]["FullJournalName"]
                pe.save()
        return pe
    
    
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
        logging.debug(text)
        # logging.debug(ref_start_position)
        ignore_pub_ids = self.__original_study_finder(doc)
        logging.debug(f"Ignore: {ignore_pub_ids}")
        
        # All citation in the text
        publication_matches = re.finditer(self.publication_regex, text)
        logging.debug(f"Above text has publications? {re.findall(self.publication_regex, text)}")
        nearest_match = None
        lowest_distance = self.INF
        for match in publication_matches:
            logging.debug(f"Checking: {match}")
            if int(match.group(3)) > self.ignore_before:
                distance = self.INF
                logging.debug(f"{match} not ignored")
                # Detect same sentence publications and take the earliest one.
                sentence = doc.char_span(match.start(0), match.end(0), alignment_mode='expand').sent.text
                same_sentence_pubs = re.finditer(self.publication_regex, sentence)
                if same_sentence_pubs:
                    for proximal_match in same_sentence_pubs:
                        if int(proximal_match.group(3)) > self.ignore_before and int(proximal_match.group(3)) > int(match.group(3)):
                            # if the same sentence has recent reference
                            # logging.debug(
                            #     f"{proximal_match.group(3)} > {match.group(3)} = {proximal_match.group(3) > match.group(3)}")
                            match = proximal_match
                # Ignore if it is found as part of "original" patient reporting study
                if ignore_pub_ids and match.group(1) in ignore_pub_ids:
                    continue
                logging.debug(f"{match} check proximity from {ref_start_position}")
                # Consider proximity of the detected publication to the anchor text
                if match.start(0) < ref_start_position:
                    distance = abs(ref_start_position - match.start(0))
                elif nearest_match is None and match.start(0) > ref_start_position:
                    distance = abs(match.start(0) - ref_start_position)
                if distance < lowest_distance:
                    nearest_match = match
                    lowest_distance = distance
        
        logging.debug(f"{nearest_match} passed proximity check")
        return nearest_match

    def __create_publication_object_from_match(self, pub_match, reference_list=None):
        ref_no = pub_match
        if isinstance(pub_match, re.Match):
            ref_no = pub_match.group(1)
        pmid = None
        if reference_list:
            for ref in reference_list:
                # print(pub_match)
                if 'referenceNumber' in ref['reference'] \
                        and ref['reference']['referenceNumber'] == int(ref_no) \
                        and 'pubmedID' in ref['reference']:
                    pmid = ref['reference']['pubmedID']
        # print(pub_match.group(0))
        pub = PublicationItem()
        pub["pmid"] = pmid
        pub["author"] = pub_match.group(2)
        pub["year"] = pub_match.group(3)
        pe = self.__get_pubmed_entry(pmid)        
        if pe != None and 'epub_date' in pe and pe.epub_date:
            pub["pub_date"] = pe.epub_date
        elif pe != None and 'pub_date' in pe and pe.pub_date:
            pub["pub_date"] = pe.pub_date
        if pe != None and 'journal_name' in pe:
            pub['journal_name'] = pe.journal_name
        return pub

    def __animal_model_type(self, name):
        """Get animal model type from the name.

        Args:
            name (str): animal model name

        Returns:
            str: animal model type
        """
        for key, val in self.animal_model_types.items():
            if name.lower() in val:
                return key
        return name

    def __closest_animal_model(self, doc, ref_position=0):
        """Get closest animal model and the closest citation to it.

        Args:
            doc (Doc): Doc representation of the text where animal models will be searched for
            ref_position (int): reference start positon. default 0.
            
        Returns:
            str: closest animal model to the reference srart position
            int: start position of the closest animal model
        """
        nearest_match = None
        lowest_distance = self.INF
        distance = lowest_distance + 1
        start_position = 0
        # Detecting animal model
        matches = self.animal_matcher(doc)
        if matches:
            for match_id, start, end in matches:
                m_span = doc[start:end]
                m_start = m_span.start_char
                # Consider proximity of the detected publication to the anchor text
                if m_start < ref_position:
                    distance = abs(ref_position - m_start)
                elif nearest_match is None and m_start > ref_position:
                    distance = abs(m_start - ref_position)
                if distance < lowest_distance:
                    nearest_match = m_span.text
                    lowest_distance = distance
                    start_position = m_start
        # if nearest_match:
        #     logging.debug(f"{doc.text[doc[start:end].start_char:10]}")
        #     logging.debug(f"Nearest match: {nearest_match}")
        #     logging.debug(doc.text)
        return nearest_match, start_position
        

    def __get_animal_model(self, text, reference_list=None, ref_start_position=0, known_publication=None, section_name=None):
        """Detect Animal model in a text

        Args:
            text (str): String represetntation of the text
            reference_list (list, optional): List of OMIMM reference. Defaults to None.
            ref_start_position (int, optional): Reference start position of the text.
                            This position will be taken into account when searching for the animal model.
                            Defaults to 0.
            known_publication (Publication, optional): If already known, the publication reference. 
                            Otherwise this function will detect. Defaults to None.
            section_name (str, optional): Name of the text section title.

        Returns:
            AnimalModelsItem: Model item for the detected animal model. 
            None: If none found retun None
        """
        text = text.replace('al.', 'al')
        paras = text.split('\n\n')
        earliest_ref = None
        anchor_location = 0
        paragraph = None
        earliest_animal = None
        
        if ref_start_position > 0:
            # Detecting the paragraph span of the reference position
            p_start = 0
            p_end = text.find('\n\n')        
            while p_end < ref_start_position:
                p_start = p_end+1
                p_end = text.find('\n\n', p_start)
                if p_end == -1:
                    p_end = len(text)
                    break
                # logging.debug(f"p_start: {p_start}, p_end: {p_end}")
                # logging.debug(f"Paragraph evaluating: {text[p_start:p_end]}")
            reletive_ref_start = ref_start_position - p_start
            paragraph = text[p_start:p_end]
            doc = self.nlp(paragraph)
            mo, ref_start = self.__closest_animal_model(doc, reletive_ref_start)
            if mo != None:                
                pub_match = self.__nearest_publication_detector(paragraph, ref_start)
                if pub_match:
                    # logging.debug(pub_match)
                    pub = self.__create_publication_object_from_match(pub_match, reference_list)
                    if earliest_animal == None or int(pub.year) < int(earliest_animal.publication_evidence.year):
                        earliest_ref = pub
                        earliest_animal = AnimalModelsItem()
                        earliest_animal.animal_name = self.__animal_model_type(mo)
                        earliest_animal.section_title = section_name
                        earliest_animal.publication_evidence = pub
        # If no animal model found in the paragraph of the reference, search in the whole text
        if earliest_animal == None:
            for p in paras:
                doc = self.nlp(p)
                mo, ref_start = self.__closest_animal_model(doc)
                if mo != None:                
                    pub_match = self.__nearest_publication_detector(p, ref_start)
                    if pub_match:
                        # logging.debug(pub_match)
                        pub = self.__create_publication_object_from_match(pub_match, reference_list)
                        if earliest_animal == None or int(pub.year) < int(earliest_animal.publication_evidence.year):
                            earliest_ref = pub
                            paragraph = p
                            earliest_animal = AnimalModelsItem()
                            earliest_animal.animal_name = self.__animal_model_type(mo)
                            earliest_animal.section_title = section_name
                            earliest_animal.publication_evidence = pub        
        return earliest_animal
        
        
    def __cohort_from_paragraph(self, paragraph, reference_list=None, section_name=None):
        """Extract cohort from a paragraph

        Args:
            paragraph (str): paragraph text
            reference_list (list, optional): List of references. Defaults to None.
            section_name (str, optional): Name of the OMIM's section. Defaults to None.
            known_publication (Publication, optional): If already known, the publication reference.

        Returns:
            list: List of cohort descriptions
            int: Total size of detected cohorts
        """
        cohorts = []
        total_cohort_size = 0
        doc = self.nlp(paragraph)
        patient_matches = self.cohort_matcher(doc)
        # logging.debug(patient_matches)
        # patient_matches = self.cohort_phrase_pattern(doc)
        if patient_matches:
            match_ids = []
            for match_id, token_ids in patient_matches:
                ignore = False
                if match_id not in match_ids:
                    cohort = CohortDescription()
                    cohort['source'] = section_name
                    _chrt_pat_name = 'cohort_pattern'
                    if len(token_ids) == 2:
                        _chrt_pat_name = 'cohort_with_det'
                    for i in range(len(token_ids)):
                        if self.cohort_pattern[_chrt_pat_name][i]["RIGHT_ID"] == 'anchor_patients':
                            cohort['cohort_type'] = doc[token_ids[i]].text
                        if self.cohort_pattern[_chrt_pat_name][i]["RIGHT_ID"] == 'patient_modifier':
                            cohort['cohort_relation'] = doc[token_ids[i]].text
                        if self.cohort_pattern[_chrt_pat_name][i]["RIGHT_ID"] == 'patient_count':
                            try:
                                if doc[token_ids[i]].text in ['a','an']:
                                    cohort['cohort_count'] = 1
                                else:
                                    cohort['cohort_count'] = w2n.word_to_num(doc[token_ids[i]].text.replace(',',''))
                                if cohort['cohort_count'] > self.max_cohort_size:
                                    ignore = True
                                    break
                                total_cohort_size += cohort['cohort_count']
                            except:
                                cohort['cohort_count'] = -1
                                logging.warning(f"Cohort count failed: {doc[token_ids[i]].text}")
                    if ignore == False:
                        nearest_pub = self.__nearest_publication_detector(
                            doc.text, doc[token_ids[0]:token_ids[1]].start_char)
                        if nearest_pub:
                            cohort['publication_evidence'] = self.__create_publication_object_from_match(nearest_pub, reference_list)
                            cohorts.append(cohort)
                        match_ids.append(match_id)
        logging.debug(f"Total Cohort Size: {total_cohort_size}")
        return cohorts, total_cohort_size
        

    def __get_cohorts(self, text, reference_list=None, ref_start_position=0, known_publication=None, section_name='molecularGenetics', ):
        """ Extract cohorts from a text. Texts can have paragraphs separated by two new lines.
        
        Args:
            text (str): Text to extract cohorts from
            reference_list (list, optional): List of references. Defaults to None.
            ref_start_position (int, optional): Reference start position of the text.
                            This position will be taken into account when searching for the animal model.
                            Defaults to 0.
            known_publication (Publication, optional): If already known, the publication reference. 
                            Otherwise this function will detect. Defaults to None.
            section_name (str, optional): Source of the text. Defaults to 'molecularGenetics'.
        
        Returns:
            list: List of cohorts
            int: Total size of detected cohorts
        """
        cohorts = []
        earliest_cohort = None
        total_cohort_size = 0
        text = text.replace('al.', 'al')
        p_start = 0
        paras = text.split('\n\n')
        already_found = False
        
        if ref_start_position > 0:
            # Detecting the paragraph span of the reference position
            p_start = 0
            p_end = text.find('\n\n')        
            while p_end < ref_start_position:
                p_start = p_end+1
                p_end = text.find('\n\n', p_start)
                if p_end == -1:
                    p_end = len(text)
                    break
                # logging.debug(f"p_start: {p_start}, p_end: {p_end}")
                # logging.debug(f"Paragraph evaluating: {text[p_start:p_end]}")
            # reletive_ref_start = ref_start_position - p_start
            paragraph = text[p_start:p_end]
            _cohorts, _total_cohort_size = self.__cohort_from_paragraph(paragraph, reference_list, section_name)
            cohorts += _cohorts
            total_cohort_size += _total_cohort_size
            # check if the cohort has same publication as the already known publication
            if _cohorts != None:
                for cohort in _cohorts:
                    if cohort.publication_evidence.pmid == known_publication.pmid:
                        earliest_cohort = cohort
                        break
        # If no cohort study found in the paragraph of the reference, search in the whole text
        if earliest_cohort == None:
            for paragraph in paras:
                if already_found == False:
                    _cohorts, _total_cohort_size = self.__cohort_from_paragraph(paragraph, reference_list, section_name)
                    cohorts += _cohorts
                    total_cohort_size += _total_cohort_size
                    # check if the cohort has same publication as the already known publication
                    if _cohorts != None and known_publication != None:
                        for cohort in _cohorts:
                            if already_found == False and cohort.publication_evidence != None and cohort.publication_evidence.pmid == known_publication.pmid:
                                earliest_cohort = cohort
                                already_found = True
                                break
        
        # If not found by reference matching above, get latest cohort study
        if earliest_cohort == None:
            for cohort in cohorts:
                if earliest_cohort == None:
                    earliest_cohort = cohort
                elif int(cohort.publication_evidence.year) < int(earliest_cohort.publication_evidence.year):
                    earliest_cohort = cohort
        return earliest_cohort, cohorts, total_cohort_size


    def __earliest_ref_from_text(self, query: str, text: str, reference_list: list, sync_matcher=None):
        """Get earliest publication reference by searching for specific text in large text.
        Text can have paragraph.

        Args:
            query (str): Query text
            text (str): Text to search
            reference_list (list): List of reference to use to extract publication releted info
            sync_matcher (Matcher, optional): Spacy Matcher function to sync
                    (cross match check/2ndary value match check) the search. Defaults to None.

        Returns:
            None: if there is no publication found
            Publication: Publication entry
        """
        # logging.debug(text)
        text = text.replace('al.', 'al')
        paras = text.split('\n\n')
        earliest_ref = None
        coreport_ref = None
        anchor_location = 0
        paragraph = None
        if not isinstance(query, list):
            query = [query]
        logging.debug(f"Looking for anchors: {query}")
        for p in paras:
            if sync_matcher:
                sync_match = sync_matcher(self.nlp(p))
            if sync_matcher == None or sync_match:
                for q in query:
                    start = p.find(str(q))
                    if start != -1:
                        pub_match = self.__nearest_publication_detector(p, start)
                        if pub_match:
                            # logging.debug(pub_match)
                            pub = self.__create_publication_object_from_match(pub_match, reference_list)
                            if earliest_ref == None or int(pub.year) < int(earliest_ref.year):
                                anchor_location = start
                                earliest_ref = pub
                                paragraph = p
        # get all reference in the section
        pubs = re.finditer(self.publication_regex, text)
        for pub in pubs:
            _cr_pub = self.__create_publication_object_from_match(pub, reference_list)
            if _cr_pub != None and earliest_ref != None:
                # get pmid date and compare
                coreport_date = _cr_pub.pub_date
                earliest_ref_date = earliest_ref.pub_date
                logging.debug(f"Potential coreport publication: {coreport_date}")
                logging.debug(f"Evidence publication: {earliest_ref_date}")
                if _cr_pub.pmid != earliest_ref.pmid and \
                    (int(_cr_pub.year) == int(earliest_ref.year) or int(_cr_pub.year) == int(earliest_ref.year)+1 or \
                    int(_cr_pub.year) == int(earliest_ref.year)-1):
                    if coreport_date != None and earliest_ref_date != None:
                        coreport_date = pendulum.instance(coreport_date)
                        epub_date = pendulum.instance(earliest_ref_date)
                        logging.debug(f"Difference of publication date: {epub_date.diff(coreport_date).in_days()}")
                        if epub_date.diff(coreport_date).in_days() < 180:
                            logging.debug(f"Coreport publication found: {_cr_pub.pmid}")
                            coreport_ref = _cr_pub
                        break
        return earliest_ref, anchor_location, paragraph, coreport_ref
    

    def process(self, item: AssociationInformation, detect='all', dry_run=False):
        """Update AssociationInformation with information extracted from related the OMIM entries.

        Args:
            item (AssociationInformation): Item to update
            detect (str, optional): What modeule/groups of information to update. Defaults to 'all'.
            dry_run (bool, optional): Run without saving it into database. Defaults to False.
        """
        if detect == 'all':
            detect = self.detection_modules
        gene_entry = GeneEntry.objects(mimNumber=item.gene_mimNumber).order_by('-mtgUpdated').first()        
        
        if gene_entry and gene_entry.geneMap is not None and 'phenotypeMapList' in gene_entry.geneMap:
            logging.debug(f"Analyzing gene: {item.gene_mimNumber}")
            known_phenotypes = gene_entry.geneMap['phenotypeMapList']
            for p in known_phenotypes:
                cohorts = []
                paragraph = None
                anchor_location = 0
                total_cohort_size = 0
                earliest_evidence = None
                known_publication = None
                earliest_animal = None
                earliest_cohort = None
                if 'phenotypeInheritance' in p['phenotypeMap'] \
                        and 'phenotype' in p['phenotypeMap'] \
                        and p['phenotypeMap']['phenotype'] \
                        and 'phenotypeMimNumber' in p['phenotypeMap'] \
                        and p['phenotypeMap']['phenotypeMimNumber'] == item.pheno_mimNumber:
                            
                    if 'basic' in detect:
                        phenotype_name = p['phenotypeMap']['phenotype']
                        for ip in self.ignore_phenotypes:
                            if ip in phenotype_name:
                                item.phenotype_marked_with = ip
                            
                    pheno_mim = item.pheno_mimNumber
                    logging.debug(f"Pheno checking: {pheno_mim}")

                    if 'basic' in detect:
                        item.gene_prefix = gene_entry.prefix
                        if 'geneMap' in gene_entry and 'geneSymbols' in gene_entry.geneMap:
                            item.gene_symbols = gene_entry.geneMap['geneSymbols']
                        if 'geneMap' in gene_entry and 'geneName' in gene_entry.geneMap:
                            item.gene_name = gene_entry.geneMap['geneName']
                    
                    ####### Look at the phenotype for available information ########
                    pheno_entry = GeneEntry.objects(mimNumber=pheno_mim).first()
                    if pheno_entry:
                        if 'basic' in detect:
                            item.pheno_prefix = pheno_entry.prefix
                        for pheno_text in pheno_entry.textSectionList:
                            
                            ####### Looking at Phenotype's Animal Model excerpt for model organism study #######
                            if 'animal' in detect and pheno_text['textSection']['textSectionName'] == 'animalModel':
                                logging.debug('----Animal Model----')
                                text = pheno_text['textSection']['textSectionContent']
                                query = []
                                if 'approvedGeneSymbols' in gene_entry.geneMap:
                                    query.append(gene_entry.geneMap['approvedGeneSymbols'])
                                query.append(gene_entry.mimNumber)
                                earliest_mo_pub, anchor_location, paragraph, coreport_ref = self.__earliest_ref_from_text(
                                    query, text, pheno_entry.referenceList, self.animal_matcher)
                                if earliest_mo_pub:
                                    earliest_animal = self.__get_animal_model(paragraph, pheno_entry.referenceList, anchor_location, earliest_mo_pub, section_name='animalModel')
                                else:
                                    earliest_animal = self.__get_animal_model(text, pheno_entry.referenceList, section_name='animalModel')

                            ####### Looking at Phenotype's Molecular Genetics for information #######
                            if earliest_evidence == None and pheno_text['textSection']['textSectionName'] == 'molecularGenetics':
                                logging.debug('----MOL-GEN----')
                                text = pheno_text['textSection']['textSectionContent']
                                query = [gene_entry.mimNumber]
                                if 'approvedGeneSymbols' in gene_entry.geneMap:
                                    query.append(gene_entry.geneMap['approvedGeneSymbols'])
                                # GDA
                                if 'association' in detect:
                                    earliest_pub, anchor_location, paragraph, coreport_ref = self.__earliest_ref_from_text(
                                        query, text, pheno_entry.referenceList)
                                    logging.debug(earliest_pub)
                                    if earliest_pub != None:
                                        evidence = Evidence()
                                        evidence.section_title = 'molecularGenetics'
                                        evidence.referred_entry = gene_entry.mimNumber
                                        evidence.publication_evidence = earliest_pub
                                        evidence.publication_coreport = coreport_ref
                                        if earliest_evidence == None or int(earliest_pub.year) < int(earliest_evidence.publication_evidence.year):
                                            earliest_evidence = evidence
                                # Animal Model
                                if 'animal' in detect and earliest_animal == None:
                                    earliest_animal = self.__get_animal_model(text, pheno_entry.referenceList, anchor_location, section_name='molecularGenetics')
                                # Cohort
                                if 'cohort' in detect and earliest_cohort == None:
                                    if earliest_evidence:
                                        known_publication = earliest_evidence.publication_evidence
                                    earliest_cohort, cohorts, tcs = self.__get_cohorts(text, pheno_entry.referenceList, 
                                                                        ref_start_position=anchor_location, known_publication=known_publication, 
                                                                        section_name="molecularGenetics")
                                    total_cohort_size += tcs

                    ####### Check Allelic variants' text for the GDA evidences ########
                    if earliest_evidence == None:
                        for allele in gene_entry.allelicVariantList:
                            if 'text' in allele['allelicVariant']:
                                logging.debug('----AV----')
                                earliest_pub, anchor_location, paragraph, coreport_ref = self.__earliest_ref_from_text(
                                    pheno_mim, allele['allelicVariant']['text'], gene_entry.referenceList)
                                if 'association' in detect:
                                    logging.debug(earliest_pub)
                                    if earliest_pub != None:
                                        evidence = Evidence()
                                        evidence.section_title = 'allelicVariant'
                                        evidence.referred_entry = pheno_mim
                                        evidence.publication_evidence = earliest_pub
                                        evidence.publication_coreport = coreport_ref
                                        if earliest_evidence == None or int(earliest_pub.year) < int(earliest_evidence.publication_evidence.year):
                                            earliest_evidence = evidence
                                if 'animal' in detect and earliest_animal == None and paragraph != None:
                                    earliest_animal = self.__get_animal_model(paragraph, gene_entry.referenceList, anchor_location, section_name='allelicVariant')
                                    
                                # Cohort
                                if 'cohort' in detect and earliest_cohort == None and paragraph != None:
                                    if earliest_evidence:
                                        known_publication = earliest_evidence.publication_evidence
                                    earliest_cohort, cohorts, tcs = self.__get_cohorts(paragraph, gene_entry.referenceList, 
                                                                        ref_start_position=anchor_location, known_publication=earliest_pub, 
                                                                        section_name="allelicVariant")
                                    total_cohort_size += tcs
                                    
                    # Add information to item
                    if 'cohort' in detect and cohorts:
                        item.all_cohorts = cohorts
                        item.total_cohort_size = total_cohort_size
                    if 'cohort' in detect and earliest_cohort:
                        item.cohort = earliest_cohort
                    if 'animal' in detect and earliest_animal:
                        item.animal_model = earliest_animal
                    if 'association' in detect and earliest_evidence:
                        item.evidence = earliest_evidence
                    if 'all' in detect:
                        item.gpad_updated = pendulum.now()
                    if dry_run == False:
                        item.save()
        else:
            logging.debug(f"GeneMap/Entry unavailable for Gene MIM {item.gene_mimNumber}")



    def curate(self, mims_to_curate: list, force_update: bool = False, detect: str = 'all', dry_run: bool = False):
        """Curate AssociationInformation entries to extract information from Entry objects

        Args:
            mims_to_curate (list): List of MIM numbers to curate. Defaults to []. If [] then all entries will be curated.
            force_update (bool, optional): Update even if the entry is already curated. Defaults to False.
            detect (str, optional): What modeule/groups of information to update. Defaults to 'all'. 
                                    Available options: 'all', 'basic', 'association', 'animal', 'cohort'
            dry_run (bool, optional): Run without saving it into database. Defaults to False.
        """
        assocs = []
        if len(mims_to_curate):
            # entries = GeneEntry.objects(mimNumber__in=mims_to_curate)
            assocs = AssociationInformation.objects(
                    (Q(gene_mimNumber__in=mims_to_curate) | Q(pheno_mimNumber__in=mims_to_curate)))
        else:
            assocs = AssociationInformation.objects
            # mims = [int(_e.mimNumber) for _e in assocs]
            # entries = GeneEntry.objects(mimNumber__in=mims)
        logging.debug(assocs)
        for assoc in tqdm(assocs, desc="Applying NLP!", colour="#fac45f"):
            if force_update or assoc.evidence == None or assoc.gpad_updated != assoc.gene_entry_fetched or assoc != assoc.pheno_entry_fetched:
                self.process(assoc, detect=detect, dry_run=dry_run)


        # entries = None
        # if len(mims_to_curate):
        #     entries = GeneEntry.objects(mimNumber__in=mims_to_curate)
        # else:
        #     gms = GeneMap.objects
        #     mims = [int(_e.mimNumber) for _e in gms]
        #     entries = GeneEntry.objects(mimNumber__in=mims)
        # for entry in tqdm(entries, desc="Applying NLP!"):
        #     curated_gene_info = CuratedGeneInfo.objects(_id=entry._id).only('_id')
        #     if curated_gene_info.count() == 0:
        #         self.process(entry)
                # item = CuratedGeneInfo()
                # self.extract_and_save(entry, item)
