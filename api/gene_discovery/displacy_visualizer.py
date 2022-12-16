import logging
from .models import GeneEntry
from tqdm import tqdm, trange
import spacy
from spacy import displacy
from word2number import w2n
from spacy.matcher import DependencyMatcher

# NUM -nummod- NOUN 
# ADJ -amod- NOUN

nlp = spacy.load("en_core_web_sm")
matcher = DependencyMatcher(nlp.vocab)

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


pattern = [
    {
        "RIGHT_ID": "anchor_verb",
        "RIGHT_ATTRS": {"POS": "VERB"} # "LEMMA": {"IN": ["describe", "report", "study", "diagnose"]}, 
    },
    {
        "LEFT_ID": "anchor_verb",
        "REL_OP": ">",
        "RIGHT_ID": "origin_modifier",
        "RIGHT_ATTRS": {"POS": "ADV", "DEP": "advmod"} # "LEMMA": {"IN": ["originally", "previously"]}, 
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

# matcher.add("PATIENTS", [pattern])
matcher.add("ORIGINAL_STUDY", [pattern])

texts = []
text_variations = {}
total_match = 0
for entry in tqdm(GeneEntry.objects[:1000]):
    for allele in entry.allelicVariantList:
        if 'text' in allele['allelicVariant']:
                text = allele['allelicVariant']['text'].replace(
                    '\n\n', ' ')
                
                doc = nlp(text)
                matches = matcher(doc)

                # logging.debug(matches)
                # Each token_id corresponds to one pattern dict
                if matches:
                    # logging.debug(text)
                    match_ids = []
                    for match_id, token_ids in matches:
                        if match_id not in match_ids:
                            total_match += 1
                            for i in range(len(token_ids)):
                                # logging.debug(pattern[i]["RIGHT_ID"] + ":", doc[token_ids[i]].text)
                                if pattern[i]["RIGHT_ID"] not in text_variations:
                                    text_variations[pattern[i]["RIGHT_ID"]] = []
                                text_variations[pattern[i]["RIGHT_ID"]].append(doc[token_ids[i]].text)
                                # logging.debug(doc[token_ids[i]].sent)
                            # logging.debug(doc[token_ids[0]:token_ids[1]].start_char)
                            # logging.debug(doc[token_ids[0]:token_ids[1]].sent)
                            # logging.debug("==========================================")
                        match_ids.append(match_id)

#                 texts.append(text)
# ss = nlp(' \n'.join(texts)).sents
# displacy.serve(ss, style="dep")

logging.debug("summary")
logging.debug(total_match)
for k, v in text_variations.items():
    logging.debug(k)
    logging.debug(set(v))