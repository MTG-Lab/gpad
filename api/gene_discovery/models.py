from mongoengine.base.fields import ObjectIdField
from mongoengine.document import Document, EmbeddedDocument, DynamicDocument
from mongoengine.fields import DateTimeField, DictField, EmbeddedDocumentField, EmbeddedDocumentListField, IntField, ListField, StringField
from .settings import *



class GeneEntry(Document):
    _id = ObjectIdField()
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
    meta = {'collection': 'gene_entry_1'}

class PublicationItem(EmbeddedDocument):
    author = StringField()
    year = IntField()
    pmid = IntField()


class MolGenItem(EmbeddedDocument):
    section_title = StringField()
    referred_entry = StringField()
    publication_evidences = EmbeddedDocumentField(PublicationItem)
    populations = ListField()


class AnimalModelsItem(EmbeddedDocument):
    animal_name = StringField()
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
    matcher_platforms = EmbeddedDocumentListField(MatcherPlatform)
    publication_evidences = EmbeddedDocumentListField(PublicationItem)
    
class Phenotype(EmbeddedDocument):
    prefix = StringField()
    mim_number = IntField()
    phenotype = StringField()
    mapping_key = IntField()
    populations = ListField()
    inheritance = StringField()
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

class CuratedGeneInfo(Document):
    _id = ObjectIdField()
    prefix = StringField()
    gene_mim_id = IntField()
    gene_symbols = StringField()
    gene_name = StringField()
    phenotypes = EmbeddedDocumentListField(Phenotype)
    molecular_genetics = EmbeddedDocumentListField(MolGenItem)
    animal_models = EmbeddedDocumentListField(AnimalModelsItem)
    date_created = DateTimeField()
    date_updated = DateTimeField()
    edit_history = ListField()
    mtg_created = DateTimeField()    # when the entry was added in MTG database
    mtg_updated = DateTimeField()    # When the enrytry was last updated in MTG database
    meta = {'collection': 'curated_gene_info_test'}

class UpdateHistory(Document):
    """Track update made for OMIM entries
    Args:
        Document (Document): [description]
    """
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
    mtgCreated = DateTimeField()    # when the entry was added in MTG database
    mtgUpdated = DateTimeField()    # When the enrytry was last updated in MTG database

class UpdatedCuratedGeneInfo(Document):
    gene_mim_id = IntField()
    gene_symbol = StringField()
    phenotypes = EmbeddedDocumentListField(Phenotype)
    molecular_genetics = EmbeddedDocumentListField(MolGenItem)
    animal_models = EmbeddedDocumentListField(AnimalModelsItem)
    date_created = DateTimeField()
    date_updated = DateTimeField()
    edit_history = ListField()
    mtg_created = DateTimeField()    # when the entry was added in MTG database
    mtg_updated = DateTimeField()    # When the enrytry was last updated in MTG database

class NCBIEntry(Document):
    meta = {'collection': 'ncbi_entry'}
    pmid = IntField()
    abstract = StringField()


class EarliestPhenotypeEvidences(Document):
    '''
    This is a view (collection) on the CuratedGeneInfo collection. This view is created manually on MongoDB database.
    '''
    gene_mim_id = IntField()
    phenotype_mim = IntField()
    phenotype = StringField()
    earliest_cohort = DictField()
    earliest_phenotype_association = DictField()
    earliest_phenotype_specific_animal_model = DictField()
    phenotype_specific_animal_model_names = ListField()
    population = ListField()
    animal_model_names = ListField()
    matcher_platform_names = ListField()
    earliest_animal_year = IntField()
    earliest_matcher_year = IntField()
    earliest_phenotype_year = IntField()
    earliest_phenotype_animal_year = IntField()
    year_created = IntField()
    year_updated = IntField()
    date_created = DateTimeField()
    date_updated = DateTimeField()
    mtg_created = DateTimeField()    # when the entry was added in MTG database
    mtg_updated = DateTimeField()    # When the enrytry was last updated in MTG database


class UpdatedAssociationEvidences(Document):
    '''
    This is a view (collection) on the UpdatedCuratedGeneInfo collection. This view is created manually on MongoDB database.
    '''
    gene_mim_id = IntField()
    phenotype_mim = IntField()
    phenotype = StringField()
    earliest_cohort = DictField()
    earliest_phenotype_association = DictField()
    earliest_phenotype_specific_animal_model = DictField()
    phenotype_specific_animal_model_names = ListField()
    population = ListField()
    animal_model_names = ListField()
    matcher_platform_names = ListField()
    earliest_animal_year = IntField()
    earliest_matcher_year = IntField()
    earliest_phenotype_year = IntField()
    earliest_phenotype_animal_year = IntField()
    year_created = IntField()
    year_updated = IntField()
    date_created = DateTimeField()
    date_updated = DateTimeField()
    mtg_created = DateTimeField()    # when the entry was added in MTG database
    mtg_updated = DateTimeField()    # When the enrytry was last updated in MTG database
    
    
class AssociationInformation(DynamicDocument):
    """
    Gene Phenotype Association object with association related information
    """
    gene_mim_id = IntField()
    phenotype_mim = IntField()
    meta = {'collection': 'latest'}
