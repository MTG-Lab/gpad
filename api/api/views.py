import datetime
import logging
from typing import DefaultDict

from bson.json_util import dumps, loads
from flask import Blueprint, current_app, jsonify, request
from flask_restful import Api, Resource
from marshmallow import ValidationError
import json
from pymongo import ASCENDING, DESCENDING
from bson import json_util

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
        gene_entry = db.db.gene_entry.find_one(_q, sort=[('dateUpdated', DESCENDING)])
        if gene_entry:
            phenos = db.db.curated_gene_info.find_one({
                'gene_mim_id': gene_entry['mimNumber']
            }, sort=[('date_updated', DESCENDING)])
            # logging.warning(phenos)
            # logging.warning(gene_entry['mimNumber'])
            # logging.warning(phenos)
            if phenos:
                for pheno in phenos['phenotypes']:
                    assoc_info = db.db.latest.find_one({
                        '$and': [
                            {'gene_mim_id': gene_entry['mimNumber']},
                            {'phenotype_mim': pheno['mim_number']}
                        ]
                    }, sort=[('date_updated', DESCENDING)])
                    # gene_info.append(assoc_info)
                    if 'earliest_phenotype_association' not in assoc_info:
                        assoc_info['earliest_phenotype_association'] = {'pmid': None, 'author': None, 'year': None}
                    if 'earliest_cohort' not in assoc_info:
                        assoc_info['earliest_cohort'] = {'publication_evidence': {'pmid': None, 'author': None, 'year': None}}
                    if 'earliest_phenotype_specific_animal_model' not in assoc_info:
                        assoc_info['earliest_phenotype_specific_animal_model'] = {'publication_evidence': {'pmid': None, 'author': None, 'year': None}}
                    gene_info.append({'gene_info': gene_entry['geneMap'], 'assoc_info': assoc_info})
        return json.loads(json.dumps(gene_info, default=json_util.default))


class NewAssociations(Resource):
    def get(self, date_from):
        date_from = datetime.datetime.fromisoformat(date_from)
        updated_genes = db.db.earliest_phenotype_association.find({
            'date_updated': {
                '$gte': date_from
            }
        })
        # logging.warning(updated_genes.count())
        # mims = [e['gene_mim_id'] for e in updated_genes]
        new_assoc = []
        for entry in updated_genes:
            query = {
                '$and': [
                    {'gene_mim_id': entry['gene_mim_id']},
                    {'phenotype_mim': entry['phenotype_mim']},
                    {'date_updated': {'$lt': date_from}}
                ]
            }
            # logging.warning(prev_update.count())
            if not db.db.earliest_phenotype_association.count_documents(query):
                new_assoc.append(entry)
                # logging.warning(f"New phenotype for: {entry['gene_mim_id']}, {entry['phenotype_mim']}")
        return json.loads(json.dumps(new_assoc, default=json_util.default)) #json.dumps(new_assoc, default=json_util.default)


class Trend(Resource):
    def get(self):
        res = db.db.latest.aggregate([
            {
                '$match': {
                    'mapping_key': {
                        '$ne': 2
                    }   
                }
            },  {
                '$set': {
                    '_id': {
                        '$concat': [
                            {
                                '$toString': '$gene_mim_id'
                            }, {
                                '$toString': '$phenotype_mim'
                            }
                        ]
                    }
                }
            }, {
                '$group': {
                    '_id': '$_id', 
                    'doc': {
                        '$last': '$$ROOT'
                    }
                }
            }, {
                '$set': {
                    'earliest_phenotype_association': '$doc.earliest_phenotype_association.year', 
                    'earliest_phenotype_specific_animal_model': '$doc.earliest_phenotype_specific_animal_model.publication_evidence.year', 
                    'earliest_cohort': '$doc.earliest_cohort.publication_evidence.year'
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
        av_res = db.db.allelic_variant.aggregate([
            {
                '$set': {
                    'earliest_av_association': '$earliest_phenotype_association.year'
                }
            }, {
                '$project': {
                    'earliest_av_association': 1
                }
            }, {
                '$facet': {
                    'earliest_av_association': [
                        {
                            '$group': {
                                '_id': '$earliest_av_association', 
                                'earliest_av_association': {
                                    '$sum': 1
                                }
                            }
                        }
                    ]
                }
            }, {
                '$unwind': {
                    'path': '$earliest_av_association'
                }
            }, {
                '$replaceRoot': {
                    'newRoot': '$earliest_av_association'
                }
            }, {
                '$group': {
                    '_id': '$_id', 
                    'earliest_av_association': {
                        '$sum': '$earliest_av_association'
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
        pheno_trend = json.loads(json.dumps(list(res), default=json_util.default))
        av_trend = json.loads(json.dumps(list(av_res), default=json_util.default))
        d = DefaultDict(dict)
        for l in (pheno_trend, av_trend):
            for elem in l:
                d[elem['_id']].update(elem)
        trend = d.values()
        return {'data': list(trend)}
        # return {'data': json.loads(json.dumps(list(res)[1:], default=json_util.default))}



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
                '$unwind': {
                    'path': '$phenotype_specific_animal_model_names'
                }
            }, {
                '$group': {
                    '_id': '$phenotype_specific_animal_model_names', 
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
            std_name = [std_name for std_name, aliases in mo.items() if entry['_id'].lower() in aliases]
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
        res = db.db.latest.aggregate(pipeline)
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
            std_name = [std_name for std_name, aliases in mo.items() if entry['_id'].lower() in aliases]
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
                        '$sum': '$earliest_cohort.cohort_count'
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
        res = db.db.latest.aggregate(pipeline)
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
