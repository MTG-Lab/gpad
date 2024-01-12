import logging
import re

import spacy
from rich import print
from spacy import displacy
from spacy.tokens import Span
from spacy.language import Language
from spacy.matcher import DependencyMatcher
from tqdm import tqdm, trange
from word2number import w2n

from api.gene_discovery.data_curation import Curator

from .models import GeneEntry
from .settings import *

# docker exec -it gpad_api python -m api.gene_discovery.displacy_visualizer


# nlp = spacy.load("en_core_web_sm")

# @Language.component("expand_person_entities")
# def expand_person_entities(doc):
#     new_ents = []
#     for ent in doc.ents:
#         if ent.label_ == "PERSON" and ent.start != 0:
#             prev_token = doc[ent.start - 1]
#             print(prev_token.label)
#             if prev_token.label in ("Dr", "Dr.", "Mr", "Mr.", "Ms", "Ms."):
#                 new_ent = Span(doc, ent.start - 1, ent.end, label=ent.label)
#                 new_ents.append(new_ent)
#         else:
#             new_ents.append(ent)
#     doc.ents = new_ents
#     return doc


# # Add the component after the named entity recognizer
# nlp.add_pipe("expand_person_entities", after="ner")

# doc = nlp("Dr. Alex Smith chaired first board meeting of Acme Corp Inc.")
# print([(ent.text, ent.label_) for ent in doc.ents])


class PatternLab:
    
    # NUM -nummod- NOUN 
    # ADJ -amod- NOUN

    text_variations = {}
    nlp = spacy.load("en_core_web_sm")
    matcher = DependencyMatcher(nlp.vocab, validate=True)
    
    matches = []

    # pattern = [
    #     {
    #         "RIGHT_ID": "anchor_patients",
    #         "RIGHT_ATTRS": {"LEMMA": {"IN": ["family", "patient", "child", "boy", "girl", "parent", "individual", "people", "infant", "woman", "man"]}, "POS": "NOUN"}
    #     },
    #     {
    #         "LEFT_ID": "anchor_patients",
    #         "REL_OP": ">",
    #         "RIGHT_ID": "patient_modifier",
    #         "RIGHT_ATTRS": {"LEMMA": {"IN": ["independent", "separate", "unrelated", "more", "different", "new", "sporadic", "further", "additional", "other"]},
    #             "DEP": "amod", "POS": "ADJ", 
    #             "ENT_TYPE": {"NOT_IN": ["NORP"],}}
    #     },
    #     {
    #         "LEFT_ID": "anchor_patients",
    #         "REL_OP": ">",
    #         "RIGHT_ID": "patient_count",
    #         "RIGHT_ATTRS": {"LIKE_NUM": True, "DEP": "nummod", "POS": "NUM"},
    #     },
    # ]


    pattern_1 = [
            {
                "RIGHT_ID": "anchor_verb",
                "RIGHT_ATTRS": {"POS": "VERB"}  # "LEMMA": {"IN": ["describe", "report", "study", "diagnose", "find"]},
            },
            {
                "LEFT_ID": "anchor_verb",
                "REL_OP": ">",
                "RIGHT_ID": "origin_modifier",
                # "LEMMA": {"IN": ["originally", "previously"]},
                "RIGHT_ATTRS": {"POS": "ADV", "DEP": "advmod", "LEMMA": {"NOT_IN": ["later", "recent", "respective"]}}
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
                "RIGHT_ID": "ref",
                "RIGHT_ATTRS": {"DEP": {"IN": ["pobj", "appos", "conj"]}, "POS": {"IN": ["NOUN", "PROPN", "NUM"]}}
            }
        ]
    pattern_2 = [
            {
                "RIGHT_ID": "anchor_verb",
                "RIGHT_ATTRS": {"POS": "VERB"}  # "LEMMA": {"IN": ["describe", "report", "study", "diagnose", "find"]},
            },
            {
                "LEFT_ID": "anchor_verb",
                "REL_OP": ">",
                "RIGHT_ID": "origin_modifier",
                # "LEMMA": {"IN": ["originally", "previously"]},
                "RIGHT_ATTRS": {"POS": "ADV", "DEP": "advmod", "LEMMA": {"NOT_IN": ["later", "recent", "respective"]}}
            },
            {
                "LEFT_ID": "anchor_verb",
                "REL_OP": ">",
                "RIGHT_ID": "agent_modifier",
                "RIGHT_ATTRS": {"POS": "ADP", "DEP": "agent"}
            },
            {
                "LEFT_ID": "anchor_verb",
                "REL_OP": ">",
                "RIGHT_ID": "ref",
                "RIGHT_ATTRS": {"DEP": {"IN": ["pobj", "appos", "conj"]}, "POS": {"IN": ["NOUN", "PROPN", "NUM"]}}
            }
        ]
    pattern_3 = [
            {
                "RIGHT_ID": "anchor_verb",
                "RIGHT_ATTRS": {"POS": "VERB"}  # "LEMMA": {"IN": ["describe", "report", "study", "diagnose", "find"]},
            },
            {
                "LEFT_ID": "anchor_verb",
                "REL_OP": ">",
                "RIGHT_ID": "origin_modifier",
                # "LEMMA": {"IN": ["originally", "previously"]},
                "RIGHT_ATTRS": {"POS": "ADV", "DEP": "advmod", "LEMMA": {"NOT_IN": ["later", "recent", "respective"]}}
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
                "RIGHT_ID": "ref",
                "RIGHT_ATTRS": {"DEP": {"IN": ["pobj", "appos", "conj"]}, "POS": {"IN": ["NOUN", "PROPN", "NUM"]}}
            },
            {
                "LEFT_ID": "ref",
                "REL_OP": ">",
                "RIGHT_ID": "ref_contd",
                "RIGHT_ATTRS": {"DEP": {"IN": ["pobj", "appos", "conj"]}, "POS": {"IN": ["NOUN", "PROPN", "NUM"]}}
            }
        ]
    cohort_phrase_pattern_1 = [
        {
            "RIGHT_ID": "anchor_patients",
            "RIGHT_ATTRS": {"LEMMA": {"IN": ["family", "patient", "child", "boy", "girl", "parent", "individual", "people", "infant", "woman", "man"]}, "POS": "NOUN"}
        },
        {
            "LEFT_ID": "anchor_patients",
            "REL_OP": ">",
            "RIGHT_ID": "patient_modifier",
            "RIGHT_ATTRS": { #"LEMMA": {"IN": ["independent", "separate", "unrelated", "more", "different", "new", "sporadic", "further", "additional", "other", "affected"]},
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
    cohort_phrase_pattern_2 = [
        {
            "RIGHT_ID": "anchor_patients",
            "RIGHT_ATTRS": {"LEMMA": {"IN": ["family", "patient", "child", "boy", "girl", "parent", "individual", "people", "infant", "woman", "man"]}, "POS": "NOUN"}
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
    
    patterns = {
        "cohort_pattern": cohort_phrase_pattern_1,
        "cohort_with_det": [
                {
                    "RIGHT_ID": "anchor_patients",
                    "RIGHT_ATTRS": {"LEMMA": {"IN": ["family", "patient", "child", "boy", "girl", "parent", "individual", "people", "infant", "woman", "man"]}, "POS": "NOUN"}
                },
                {
                    "LEFT_ID": "anchor_patients",
                    "REL_OP": ">",
                    "RIGHT_ID": "patient_count_1",
                    "RIGHT_ATTRS": {"DEP": "det", "POS": "DET", "LEMMA": {"IN": ["a", "an"]}},
                },
        ],
        "cohort_with_num": [
                {
                    "RIGHT_ID": "anchor_patients",
                    "RIGHT_ATTRS": {"LEMMA": {"IN": ["family", "patient", "child", "boy", "girl", "parent", "individual", "people", "infant", "woman", "man"]}, "POS": "NOUN"}
                },
                {
                    "LEFT_ID": "anchor_patients",
                    "REL_OP": ">",
                    "RIGHT_ID": "patient_count_2",
                    "RIGHT_ATTRS": {"LIKE_NUM": True, "DEP": "nummod", "POS": "NUM"},
                },
        ],
    }
    
    def __init__(self, pattern="cohort_pattern") -> None:
        if type(pattern) == str:
            self.active_pattern = pattern
            self.matcher.add(pattern, [self.patterns[pattern]])
        else:
            for p in pattern:
                self.matcher.add(p, [self.patterns[p]])

    def show(self, text):
        options = {"compact": True, "bg": "#09a3d5",
           "color": "white", "font": "Source Sans Pro"}
        ss = self.nlp(text).sents
        displacy.serve(ss, style="dep", options=options)
        
    def on_cohort_match(self, matcher, doc, match_id, matches):
        # logging.debug(f"MATCH ID: {match_id}")
        # logging.debug(f"# of PATIENTS: {doc[matches[match_id][1][1]]}")
        # for match_id, token_ids in matches:
        #     # refs.append(doc[token_ids[2]])
        #     _match_text = []
        #     for i in range(len(token_ids)):
        #         _match_text.append(doc[token_ids[i]])
        #     logging.info(' '.join(_match_text))
        
        match_ids = []
        for match_id, token_ids in matches:
            logging.info(f"SENTANCE: {doc[token_ids[0]].sent}")
            m_span = []
            for i in range(len(token_ids)):
                # logging.debug(f"ID {self.pattern[i]['RIGHT_ID']} : {doc[token_ids[i]]}")
                logging.debug(f"==> {i}: {doc[token_ids[i]]}")
                # if self.patterns[self.active_pattern][i]["RIGHT_ID"] not in self.text_variations:
                #     self.text_variations[self.patterns[self.active_pattern][i]["RIGHT_ID"]] = []
                # self.text_variations[self.patterns[self.active_pattern][i]["RIGHT_ID"]].append(doc[token_ids[i]].text)
                logging.debug(f"POS:{doc[token_ids[i]].pos_}")
                logging.debug(f"DEP:{doc[token_ids[i]].dep_}")
                m_span.append(doc[token_ids[i]].text)
            # logging.debug(doc[token_ids[0]:token_ids[1]].start_char)
            # logging.debug(doc[token_ids[0]:token_ids[1]].sent)
            logging.debug("==========================================")
            match_ids.append(match_id)
            logging.info(f"SPAN: {m_span}")
        logging.debug(f"ALL THE MATCHES: {list(set(self.matches))}")
        logging.debug(f"TEXT VARIATIONS: {self.text_variations}")
        

    def vm(self, text):
        doc = self.nlp(text)
        matches = self.matcher(doc)
        text = []
        matched_texts = {}
        # iterate over the matches
        for match_id, token_ids in matches:
            _match_text = []
            for i in range(len(token_ids)):
                _match_text.append(doc[token_ids[i]].text)
                if len(matched_texts) > i:
                    matched_texts[i].append(doc[token_ids[i]].text)
                else:
                    matched_texts[i] = [doc[token_ids[i]].text]
            logging.debug(" ".join(_match_text))
            logging.debug(f" ")
        return matched_texts
        
    def on_match(self, matcher, doc, match_id, matches):
        string_id = doc.vocab.strings[match_id]
        # logging.debug(f" MATCHER: {matcher}")
        # logging.debug(f" MATCH ID: {matcher}")
        logging.debug(f" MATCH ID: {doc[matches[match_id][1][2]]}")
        # logging.debug(f"# of Matches: {len(matches)}")
        
        # logging.debug(text)
        refs = []
        total = 0
        for match_id, token_ids in matches:
            refs.append(doc[token_ids[2]])
            total += int(doc[token_ids[2]].text)
            # logging.debug(f"SENTANCE: {doc[token_ids[0]].sent}")
            # logging.debug(f"TOKENS: {token_ids}")
            _match_text = []
            for i in range(len(token_ids)):
                # refs.append(doc[token_ids[2]])
                _match_text.append(doc[token_ids[i]])
            #     # logging.debug(f"==> {i}: {doc[token_ids[i]]}")
            #     # logging.debug(f"POS:{doc[token_ids[i]].pos_}")
            #     # logging.debug(f"DEP:{doc[token_ids[i]].dep_}")
            logging.debug(_match_text)
        logging.debug(f"# of patients: {refs}")
        logging.debug(f"TOTAL: {total}")
        self.matches += list(set(refs))
        logging.debug("==========================================")
        
        
    def match(self, text):
        doc = self.nlp(text)
        matches = self.matcher(doc)
    
        # Each token_id corresponds to one pattern dict
        
        # if matches:
        #     total = 0
        #     for match_id, token_ids in matches:
        #         w = doc[token_ids[1]].text
        #         num = w2n.word_to_num(w.replace(',',''))
        #         logging.debug(num)
        #         total += int(num)
        #     logging.debug(f"TOTAL=======: {total}========")
        
        if matches:
            logging.debug(text)
            match_ids = []
            for match_id, token_ids in matches:
                logging.info(f"SENTANCE: {doc[token_ids[0]].sent}")
                m_span = []
                for i in range(len(token_ids)):
                    # logging.debug(f"ID {self.pattern[i]['RIGHT_ID']} : {doc[token_ids[i]]}")
                    logging.debug(f"==> {i}: {doc[token_ids[i]]}")
                    # if self.patterns[self.active_pattern][i]["RIGHT_ID"] not in self.text_variations:
                    #     self.text_variations[self.patterns[self.active_pattern][i]["RIGHT_ID"]] = []
                    # self.text_variations[self.patterns[self.active_pattern][i]["RIGHT_ID"]].append(doc[token_ids[i]].text)
                    logging.debug(f"POS:{doc[token_ids[i]].pos_}")
                    logging.debug(f"DEP:{doc[token_ids[i]].dep_}")
                    m_span.append(doc[token_ids[i]].text)
                # logging.debug(doc[token_ids[0]:token_ids[1]].start_char)
                # logging.debug(doc[token_ids[0]:token_ids[1]].sent)
                logging.debug("==========================================")
                match_ids.append(match_id)
                logging.info(f"SPAN: {m_span}")
        logging.debug(f"ALL THE MATCHES: {list(set(self.matches))}")
        logging.debug(f"TEXT VARIATIONS: {self.text_variations}")
        return matches
    
def mask_citation(match):
#    return f"Ref#{match.group(1)}" 
   return f"Ref#{match.group(1)} ({match.group(3)})" 
    

# for k, v in text_variations.items():
#     logging.debug(k)
#     logging.debug(set(v))