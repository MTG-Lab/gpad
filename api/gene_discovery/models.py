import pandas as pd
from mongoengine.base.fields import ObjectIdField
from mongoengine.document import Document, EmbeddedDocument, DynamicDocument
from mongoengine.fields import DateTimeField, DictField, EmbeddedDocumentField, EmbeddedDocumentListField, IntField, ListField, StringField, BooleanField
from .settings import *



class GeneEntry(Document):
    _id = ObjectIdField(primary_key=True)
    prefix = StringField()
    mimNumber = IntField()
    status = StringField()
    titles = DictField()
    creationDate = StringField()
    editHistory = StringField()
    epochCreated = IntField()
    dateCreated = DateTimeField()
    epochUpdated = IntField()
    dateUpdated = DateTimeField()
    textSectionList = ListField()
    allelicVariantList = ListField()
    referenceList = ListField()
    geneMap = DictField()
    externalLinks = DictField()
    mtgCreated = DateTimeField()    # when the entry was added in GPAD database
    mtgUpdated = DateTimeField()    # When the enrytry was last updated in GPAD database
    meta = {'collection': 'omim_entry'} # entry


class PublicationItem(EmbeddedDocument):
    author = StringField()
    year = IntField()
    pmid = IntField()
    pub_date = DateTimeField()

class Evidence(EmbeddedDocument):
    section_title = StringField()
    referred_entry = IntField()
    publication_evidence = EmbeddedDocumentField(PublicationItem)
    populations = ListField()
    
class AnimalModelsItem(EmbeddedDocument):
    animal_name = StringField()
    section_title = StringField()
    publication_evidence = EmbeddedDocumentField(PublicationItem)

class MatcherPlatform(EmbeddedDocument):
    platform_name = StringField()
    publication_evidence = EmbeddedDocumentField(PublicationItem)

class CohortDescription(EmbeddedDocument):
    # TODO: Also include population here? making it attachable to the cohort info
    cohort_count = IntField()
    cohort_relation = StringField()
    cohort_type = StringField()
    source = StringField()
    publication_evidence = EmbeddedDocumentField(PublicationItem)

class AllelicVariant(EmbeddedDocument):
    name = StringField()
    cohorts = EmbeddedDocumentListField(CohortDescription)
    animal_models = EmbeddedDocumentListField(AnimalModelsItem)
    publication_evidences = EmbeddedDocumentListField(PublicationItem)
    
class Phenotype(EmbeddedDocument):
    prefix = StringField()
    mimNumber = IntField()
    phenotype = StringField()
    mapping_key = IntField()
    populations = ListField()
    inheritance = StringField()
    # molecular_genetics = EmbeddedDocumentField(MolGenItem)
    allelic_variants = EmbeddedDocumentListField(AllelicVariant)
    cohorts = EmbeddedDocumentListField(CohortDescription)
    animal_models = EmbeddedDocumentListField(AnimalModelsItem)
    matcher_platforms = EmbeddedDocumentListField(MatcherPlatform)
    publication_evidences = EmbeddedDocumentListField(PublicationItem)
    omim_entry_fetched = DateTimeField()


class GeneMap(Document):
    _id = ObjectIdField()
    mimNumber = IntField()
    geneSymbols = StringField()
    geneName = StringField()
    geneIDs = StringField()
    ensemblIDs = StringField()
    approvedGeneSymbols = StringField()
    phenotypes = EmbeddedDocumentListField(Phenotype)
    omim_entry_fetched = DateTimeField()
    gpad_created = DateTimeField()
    gpad_updated = DateTimeField()

   

class AssociationInformation(DynamicDocument):
    """
    Gene Phenotype Association object with association related information
    """
    gene_mimNumber = IntField()
    pheno_mimNumber = IntField()
    
    gene_prefix = StringField()
    pheno_prefix = StringField()
    
    gene_symbols = StringField()
    gene_name = StringField()
    phenotype = StringField()
    has_gene_entry = BooleanField()
    has_pheno_entry = BooleanField()
    
    mapping_key = IntField()
    inheritance = StringField()
    
    # Dervied indicators
    phenotype_marked_with = StringField()
    
    ### Identified information ###
    # Major
    evidence = EmbeddedDocumentField(Evidence)    
    animal_model = EmbeddedDocumentField(AnimalModelsItem)  
    cohort = EmbeddedDocumentField(CohortDescription)
    # Secondary
    all_cohorts = EmbeddedDocumentListField(CohortDescription)
    # populations = ListField()
    # allelic_variants = EmbeddedDocumentListField(AllelicVariant)
    total_cohort_size = IntField()
    total_unrelated_cohort_size = IntField()    
    
    # Time stamps
    omim_entry_fetched = DateTimeField()
    gene_entry_fetched = DateTimeField()
    pheno_entry_fetched = DateTimeField()
    gpad_created = DateTimeField()    # when the entry was added in GPAD database
    gpad_updated = DateTimeField()    # When the enrytry was last updated in GPAD database
    meta = {'collection': 'association_information_test_2'} # 'assocaiton_information'
    

class PubmedEntry(Document):
    pmid = IntField()
    abstract = StringField()
    raw_pub_date = StringField()
    raw_epub_date = StringField()
    pub_date = DateTimeField()
    epub_date = DateTimeField()
    pub_year = StringField()
    meta = {'collection': 'pubmed_entry'}





class AggregationQueryFactory:
    
    flatten_association = [
                {
                    '$project': {
                        '_id': '$_id', 
                        'gene_mimNumber': '$gene_mimNumber', 
                        'pheno_mimNumber': '$pheno_mimNumber', 
                        'gene_prefix': '$gene_prefix', 
                        'pheno_prefix': '$pheno_prefix', 
                        'gene_symbols': '$gene_symbols', 
                        'gene_name': '$gene_name', 
                        'phenotype': '$phenotype', 
                        'mapping_key': '$mapping_key', 
                        'inheritance': '$inheritance', 
                        'evidence': '$evidence', 
                        'evidence_section': '$evidence.section_title', 
                        'evidence_referred_entry': '$evidence.referred_entry', 
                        'evidence_publication_evidence': '$evidence.publication_evidence', 
                        'evidence_publication_evidence_author': '$evidence.publication_evidence.author', 
                        'evidence_publication_evidence_year': '$evidence.publication_evidence.year', 
                        'evidence_publication_evidence_pmid': '$evidence.publication_evidence.pmid', 
                        'animal_model': '$animal_model', 
                        'animal_model_animal_name': '$animal_model.animal_name', 
                        'animal_model_section_title': '$animal_model.section_title', 
                        'animal_model_publication_evidence': '$animal_model.publication_evidence', 
                        'animal_model_publication_evidence_author': '$animal_model.publication_evidence.author', 
                        'animal_model_publication_evidence_year': '$animal_model.publication_evidence.year', 
                        'animal_model_publication_evidence_pmid': '$animal_model.publication_evidence.pmid', 
                        'cohort': '$cohort', 
                        'matcher_platforms': '$matcher_platforms', 
                        'omim_entry_fetched': '$omim_entry_fetched', 
                        'gene_entry_fetched': '$gene_entry_fetched', 
                        'pheno_entry_fetched': '$pheno_entry_fetched', 
                        'gpad_created': '$gpad_created', 
                        'gpad_updated': '$gpad_updated'
                    }
                }
            ]
    
    def __init__(self, document_obj=None) -> None:
        self.object = document_obj        
    
    

    def flatten_data(self, y):
        out = {}

        def flatten(x, name=''):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + '_')
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '_')
                    i += 1
            else:
                out[name[:-1]] = x

        flatten(y)
        return out

    
    def export_associations(self, output_filename):    
        d = [self.flatten_data(ob.to_mongo().to_dict()) for ob in AssociationInformation.objects]
        df = pd.DataFrame.from_dict(d)
        df.to_excel(output_filename, sheet_name="GPAD", index=False)
