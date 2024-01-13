import datetime
import logging
from typing import DefaultDict

from flask_cors import CORS
from bson.json_util import dumps, loads
from flask import Blueprint, current_app, jsonify, request
from flask_restful import Api, Resource
from marshmallow import ValidationError
import json
from pymongo import ASCENDING, DESCENDING
from bson import json_util
from api.gene_discovery.models import GeneEntry, AssociationInformation

from api.extensions import apispec, db

# from api.api.resources import UserResource, UserList
# from api.api.schemas import UserSchema


blueprint = Blueprint("api", __name__, url_prefix="/api/v1")
api = Api(blueprint)


class Search(Resource):
    def get(self):
        query = request.args.get('q')
        gene_info = []
        _q = {'$text': { '$search': query }}
        if query.isnumeric():
            _q = {'mimNumber': int(query)}
        omim_entry = db.db[GeneEntry._get_collection_name()].find(_q, sort=[('dateUpdated', DESCENDING)])
        if omim_entry:
            for oe in omim_entry:
                logging.info(oe['mimNumber'])
                gdas = db.db[AssociationInformation._get_collection_name()].find(
                    {'$or': [
                        {'gene_mimNumber': oe['mimNumber']},
                        {'pheno_mimNumber': oe['mimNumber']}
                ]}, sort=[('date_updated', DESCENDING)])
                for assoc_info in gdas:
                    if assoc_info:
                        if 'evidence' not in assoc_info:
                            assoc_info['evidence'] = {'publication_evidence': {'pmid': None, 'author': None, 'year': None}}
                        if 'cohort' not in assoc_info:
                            assoc_info['cohort'] = {'publication_evidence': {'pmid': None, 'author': None, 'year': None}}
                        if 'animal_model' not in assoc_info:
                            assoc_info['animal_model'] = {'publication_evidence': {'pmid': None, 'author': None, 'year': None}}
                        gene_info.append({'assoc_info': assoc_info})
        return json.loads(json.dumps(gene_info, default=json_util.default))


class NewAssociations(Resource):
    def get(self, date_from):
        sort = [('evidence.publication_evidence.year', -1), ('gpad_updated', -1)]
        recent_entries = db.db[AssociationInformation._get_collection_name()].find().sort(sort).limit(5)
        return json.loads(json.dumps(list(recent_entries), default=json_util.default))

class Trend(Resource):
    def get(self):
        # logging.info('trend')
        res = db.db[AssociationInformation._get_collection_name()].aggregate([
            {
                '$group': {
                    '_id': '$_id', 
                    'doc': {
                        '$last': '$$ROOT'
                    }
                }
            }, {
                '$set': {
                    'earliest_phenotype_association': '$doc.evidence.publication_evidence.year', 
                    'earliest_phenotype_specific_animal_model': '$doc.animal_model.publication_evidence.year', 
                    'earliest_cohort': '$doc.cohort.publication_evidence.year'
                }
            }, {
                '$project': {
                    'earliest_phenotype_association': 1, 
                    'earliest_phenotype_specific_animal_model': 1, 
                    'earliest_cohort': 1
                }
            }, {
                '$facet': {
                    'earliest_phenotype_association': [
                        {
                            '$group': {
                                '_id': '$earliest_phenotype_association', 
                                'earliest_phenotype_association': {
                                    '$sum': 1
                                }
                            }
                        }
                    ], 
                    'earliest_cohort': [
                        {
                            '$group': {
                                '_id': '$earliest_cohort', 
                                'earliest_cohort': {
                                    '$sum': 1
                                }
                            }
                        }
                    ], 
                    'earliest_phenotype_specific_animal_model': [
                        {
                            '$group': {
                                '_id': '$earliest_phenotype_specific_animal_model', 
                                'earliest_phenotype_specific_animal_model': {
                                    '$sum': 1
                                }
                            }
                        }
                    ]
                }
            }, {
                '$set': {
                    'years': {
                        '$concatArrays': [
                            '$earliest_phenotype_association', '$earliest_cohort', '$earliest_phenotype_specific_animal_model'
                        ]
                    }
                }
            }, {
                '$project': {
                    'years': 1
                }
            }, {
                '$unwind': {
                    'path': '$years'
                }
            }, {
                '$replaceRoot': {
                    'newRoot': '$years'
                }
            }, {
                '$group': {
                    '_id': '$_id', 
                    'earliest_phenotype_association': {
                        '$sum': '$earliest_phenotype_association'
                    }, 
                    'earliest_cohort': {
                        '$sum': '$earliest_cohort'
                    }, 
                    'earliest_phenotype_specific_animal_model': {
                        '$sum': '$earliest_phenotype_specific_animal_model'
                    }
                }
            }, {
                '$match': {
                    '_id': {
                        '$gt': 1982
                    }
                }
            }, {
                '$sort': {
                    '_id': 1
                }
            }
        ])

        return {'data': json.loads(json.dumps(list(res)[1:], default=json_util.default))}



class VariantAssociationTrend(Resource):
    def get(self):
        res = db.db.allelic_variant.aggregate([
                {
                    '$set': {
                        'earliest_phenotype_association': '$earliest_phenotype_association.year', 
                        'earliest_phenotype_specific_animal_model': '$earliest_phenotype_specific_animal_model.publication_evidence.year', 
                        'earliest_cohort': '$earliest_cohort.publication_evidence.year'
                    }
                }, {
                    '$project': {
                        'earliest_phenotype_association': 1, 
                        'earliest_phenotype_specific_animal_model': 1, 
                        'earliest_cohort': 1
                    }
                }, {
                    '$facet': {
                        'earliest_phenotype_association': [
                            {
                                '$group': {
                                    '_id': '$earliest_phenotype_association', 
                                    'earliest_phenotype_association': {
                                        '$sum': 1
                                    }
                                }
                            }
                        ], 
                        'earliest_cohort': [
                            {
                                '$group': {
                                    '_id': '$earliest_cohort', 
                                    'earliest_cohort': {
                                        '$sum': 1
                                    }
                                }
                            }
                        ], 
                        'earliest_phenotype_specific_animal_model': [
                            {
                                '$group': {
                                    '_id': '$earliest_phenotype_specific_animal_model', 
                                    'earliest_phenotype_specific_animal_model': {
                                        '$sum': 1
                                    }
                                }
                            }
                        ]
                    }
                }, {
                    '$set': {
                        'years': {
                            '$concatArrays': [
                                '$earliest_phenotype_association', '$earliest_cohort', '$earliest_phenotype_specific_animal_model'
                            ]
                        }
                    }
                }, {
                    '$project': {
                        'years': 1
                    }
                }, {
                    '$unwind': {
                        'path': '$years'
                    }
                }, {
                    '$replaceRoot': {
                        'newRoot': '$years'
                    }
                }, {
                    '$group': {
                        '_id': '$_id', 
                        'earliest_phenotype_association': {
                            '$sum': '$earliest_phenotype_association'
                        }, 
                        'earliest_cohort': {
                            '$sum': '$earliest_cohort'
                        }, 
                        'earliest_phenotype_specific_animal_model': {
                            '$sum': '$earliest_phenotype_specific_animal_model'
                        }
                    }
                }, {
                    '$match': {
                        '_id': {
                            '$gt': 1985
                        }
                    }
                }, {
                    '$sort': {
                        '_id': 1
                    }
                }
            ])
        return {'data': json.loads(json.dumps(list(res)[1:], default=json_util.default))}


class ModelOrganismTrend(Resource):
    def get(self):
        pipeline = [
            {
                '$set': {
                    'mo': '$animal_model.animal_name'
                }
            }, {
                '$unwind': {
                    'path': '$mo'
                }
            }, {
                '$group': {
                    '_id': '$mo', 
                    'count': {
                        '$sum': 1
                    }
                }
            }
        ]
        res = db.db[AssociationInformation._get_collection_name()].aggregate(pipeline)
        mo = {
            'Yeast': ["saccharomyces cerevisiae", "s. cerevisiae", "yeast"], 
            'Pea Plant': ["pisum sativum", "Pea plant"], 
            'Drosophila': ["drosophila melanogaster", "d. melanogaster", "drosophila", "fruit fly"], 
            'C. elegans': ["caenorhabditis elegans", "c. elegans", "roundworm", "worm"], 
            'Zebrafish': ["danio rerio", "Zebra fish", "zebrafish"], 
            'Mouse': ["mus musculus", "mouse", "mice"],
            'Rat/Rodents': ["rattus norvegicus", "rat", "rodent", "avian"],
            'Xenopus': ['xenopus'], 
            'Other': ["cattle", "bull", "chicken", "dog"]
        }
        data = {}
        for entry in res:
            std_name = []
            # Check if entry is in any of the aliases
            for _std_name, aliases in mo.items():
                if entry['_id'].lower() in aliases:
                    logging.info(_std_name)
                    std_name.append(_std_name)
                    break
            if not std_name:
                std_name.append('Other')

            # Initialize dict if not present
            if std_name[0] in data.keys():
                data[std_name[0]] += int(entry['count'])
            else:
                data[std_name[0]] = int(entry['count'])
        items = []
        for k, v in data.items():
            items.append({'_id': k, 'count': v})
        return {'data': items}



class ModelOrganismYearlyTrend(Resource):
    def get(self):
        pipeline = [
            {
                '$set': {
                    'phenotype_specific_animal_model_names': '$animal_model.animal_name',
                    'earliest_phenotype_animal_year': '$animal_model.publication_evidence.year',
                }
            }, {
                '$unwind': {
                    'path': '$phenotype_specific_animal_model_names'
                }
            }, {
                '$group': {
                    '_id': {
                        'name': '$phenotype_specific_animal_model_names', 
                        'year': '$earliest_phenotype_animal_year'
                    }, 
                    'count': {
                        '$sum': 1
                    }
                }
            }, {
                '$set': {
                    '_id': '$_id.name', 
                    'year': '$_id.year'
                }
            }, {
                '$sort': {
                    'year': 1, 
                    'count': -1
                }
            }
        ]
        res = db.db[AssociationInformation._get_collection_name()].aggregate(pipeline)
        mo = {
            'Yeast': ["saccharomyces cerevisiae", "s. cerevisiae", "yeast"], 
            'Pea Plant': ["pisum sativum", "Pea plant"], 
            'Drosophila': ["drosophila melanogaster", "d. melanogaster", "drosophila", "fruit fly"], 
            'C. elegans': ["caenorhabditis elegans", "c. elegans", "roundworm", "worm", "worms"], 
            'Zebrafish': ["danio rerio", "Zebra fish", "zebrafish"], 
            'Mouse': ["mus musculus", "mouse", "mice"],
            'Rat/Rodents': ["rattus norvegicus", "rat", "rodent", "avian", "rats"],
            'Xenopus': ['xenopus'], 
            'Other': ["cattle", "bull", "chicken", "dog"]
        }
        data = {}
        c = 0
        for entry in res:            
            std_name = []
            # Check if entry is in any of the aliases
            for _std_name, aliases in mo.items():
                if entry['_id'].lower() in aliases:
                    logging.info(_std_name)
                    std_name.append(_std_name)
                    break
            if not std_name:
                std_name.append('Other')
            # std_name = [std_name for std_name, aliases in mo.items() if entry['_id'].lower() in aliases]
            if entry['year'] in data.keys():
                if std_name[0] in data[entry['year']].keys():
                    data[entry['year']][std_name[0]] += int(entry['count'])
                else:
                    data[entry['year']][std_name[0]] = int(entry['count'])
                c += entry['count']
                # logging.warning(data)
            else:
                data[entry['year']] = {std_name[0]: int(entry['count'])}
        # logging.warning(c)
        items = []
        c = 0
        for k, v in data.items():
            if k > 2000:
                for org, count in v.items():
                    # logging.warning(org)
                    items.append({'year': k, org: count})
                    c += count
        # logging.warning(c)
        # logging.warning(len(items))
        return {'data': items}

class CohortCount(Resource):
    def get(self):
        pipeline = [
            {
                '$set': {
                    'cohort_count': {
                        '$sum': '$cohort.cohort_count'
                    }
                }
            }, {
            #     '$match': {
            #         'cohort_count': {
            #             '$eq': 1
            #         }
            #     }
            # }, {
                '$project': {
                    'cohort_count': 1
                }
            }
        ]
        res = db.db[AssociationInformation._get_collection_name()].aggregate(pipeline)
        data = {"1": 0, "2-5": 0, '5-10': 0, '10+': 0}
        for entry in res:
            # logging.warning(entry['cohort_count'])
            if entry['cohort_count'] == 1:
                data["1"] += 1
            elif entry['cohort_count'] > 1 and entry['cohort_count'] <=5:
                data["2-5"] += 1
            elif entry['cohort_count'] > 5 and entry['cohort_count'] <=10:
                data["5-10"] += 1
            elif entry['cohort_count'] > 10:
                data["10+"] += 1
        items = []
        for k, v in data.items():
            items.append({'name': k, 'value': v})
        return {'data': items}
        

class PopulationTrend(Resource):
    def get(self):
        pipeline = [
            {
                '$unwind': {
                    'path': '$population'
                }
            }, {
                '$group': {
                    '_id': '$population', 
                    'count': {
                        '$sum': 1
                    }
                }
            }, {
                '$sort': {
                    'count': -1
                }
            }
        ]
        res = db.db.latest.aggregate(pipeline)
        items = []
        for entry in res:
            # TODO: change population discovery strategy/pattern
            if entry['_id'] != 'Sanger' and len(entry['_id']) > 4 and entry['count'] > 2 and not any(i.isdigit() for i in entry['_id']):
                items.append({
                    '_id': entry['_id'],
                    'count': entry['count']
                })
        return {'data': items}





api.add_resource(Search, '/search')
api.add_resource(NewAssociations, '/new/<string:date_from>')
api.add_resource(Trend, '/trend')
api.add_resource(VariantAssociationTrend, '/av_trend')
api.add_resource(ModelOrganismTrend, '/mo_trend')
api.add_resource(ModelOrganismYearlyTrend, '/mo_yearly_trend')
api.add_resource(CohortCount, '/cohorts')
api.add_resource(PopulationTrend, '/population_trend')


# api.add_resource(UserResource, "/users/<int:user_id>", endpoint="user_by_id")
# api.add_resource(UserList, "/users", endpoint="users")


# @blueprint.before_app_first_request
# def register_views():
#     apispec.spec.components.schema("UserSchema", schema=UserSchema)
#     apispec.spec.path(view=UserResource, app=current_app)
#     apispec.spec.path(view=UserList, app=current_app)


@blueprint.errorhandler(ValidationError)
def handle_marshmallow_error(e):
    """Return json error for marshmallow validation errors.

    This will avoid having to try/catch ValidationErrors in all endpoints, returning
    correct JSON response with associated HTTP 400 Status (https://tools.ietf.org/html/rfc7231#section-6.5.1)
    """
    return jsonify(e.messages), 400
