// init-mongo.js
db = db.getSiblingDB('gene_discovery');  // Create new database or connect to it if it already exists

// Create collections
db.createCollection("omim_entry");  // For saving OMIM entries
db.createCollection("association_information_test_2");  // For saving association information after curation

// Create indexes for collections
db.omim_entry.createIndex([
    { v: 2, key: { _id: 1 }, name: '_id_' },
    {
      v: 2,
      key: { _fts: 'text', _ftsx: 1 },
      name: 'text',
      background: false,
      weights: {
        'geneMap.approvedGeneSymbols': 1,
        'geneMap.ensemblIDs': 1,
        'geneMap.geneName': 1,
        'geneMap.geneSymbols': 1
      },
      default_language: 'english',
      language_override: 'language',
      textIndexVersion: 3
    },
    { v: 2, key: { _cls: 1 }, name: '_cls_1', background: false }
  ]); 

