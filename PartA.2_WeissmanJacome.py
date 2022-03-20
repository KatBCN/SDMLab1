import numpy as np
import py2neo
import random

graph = py2neo.Graph("bolt://localhost:7687", user='neo4j', password='1234katmat')

random.seed(42)
np.random.seed(42)

### Initial loading
def load_journals(filename):
    with open('Cypher queries/CYPHER_journals_creation.txt', 'r') as queryfile:
        query = queryfile.read().format(filename)
        graph.run(query)
        print('Loaded {} into the DB!'.format(filename))


def load_conferences(filename):
    with open('Cypher queries/CYPHER_conferences_creation.txt', 'r') as queryfile:
        query = queryfile.read().format(filename)
        graph.run(query)
        print('Loaded {} into the DB!'.format(filename))


def create_corresponding_authors(filename):
    with open('Cypher queries/CYPHER_corresponding_authors.txt', 'r') as queryfile:
        query = queryfile.read().format(filename)
        graph.run(query)
        print('Loaded {}\'s corr. auth. into the DB!'.format(filename))


#define desired journals and conferences
journals = ['BigDataMiningAndAnalytics',
            'IEEETransactionsOnBigData',
            'DataIntelligence']
conferences = ['IEEE_ACM_BDCAT',
               'IEEE_BigComp']

#load data into the database
for journal in journals:
    load_journals(journal)
for conf in conferences:
    load_conferences(conf)
for element in journals + conferences:
    create_corresponding_authors(element)


### Keyword generator
def random_keywords():
    n = np.random.randint(1, 3)

    keywords = ['Data Management', 'Indexing', 'Data Modeling', 'Big Data',
                'Data Processing', 'Data Storage', 'Data Querying']

    assign_list = random.sample(keywords, n)
    return assign_list


def load_keywords():
    keywords = ['Data Management', 'Indexing', 'Data Modeling', 'Big Data',
                'Data Processing', 'Data Storage', 'Data Querying']
    for kw in keywords:
        graph.run('CREATE (n:Keyword {{topic: \'{}\'}}) '.format(kw))


def assign_keywords():
    paper_ids = graph.run('match (n:Paper) return ID(n) as id').to_data_frame()['id']

    for paper_id in paper_ids:
        keywords = random_keywords()
        for kw in keywords:
            graph.run('MATCH (p:Paper), (k:Keyword) WHERE ID(p) = {paper_id}'
                      ' AND k.topic = \'{kw}\' MERGE (p)-[:DISCUSSES]->(k)'.format(paper_id=paper_id,
                                                                              kw=kw))


#run functions
load_keywords()
assign_keywords()


### Citation generator
def get_chronological_ids():         #THE QUERY IS PROBLEMATIC RIGHT NOW. REPEATED IDs come up.
    query = 'MATCH(author:Author)-[:WROTE {role:"corresponding"}]->' \
            '(paper:Paper)-[:PUBLISHED_IN]->(volumeEdition)-[]->(journalConference) ' \
            'RETURN ID(paper) as id, author.name as author, paper.title as title, ' \
            'volumeEdition.title as volumeEdition, volumeEdition.year as year, ' \
            'journalConference.title as journalConference ' \
            'ORDER BY year'

    sorted_papers = graph.run(query).to_data_frame()
    dct = dict(zip(sorted_papers.index, sorted_papers['id']))
    return dct


def assign_citations():
    chrono_ids = get_chronological_ids()

    for key in chrono_ids.keys():
        n = np.random.randint(1, 14)
        highest = len(chrono_ids.keys())
        lowest = key - highest
        rnge = list(range(lowest,key))

        potentially_cited = random.sample(rnge, n)
        cited_db_ids = [chrono_ids[x] for x in potentially_cited if x > 0] or None
        print(key, chrono_ids[key], cited_db_ids)

        if cited_db_ids is not None:
            for db_id in cited_db_ids:
                assert db_id != chrono_ids[key]
                query = 'MATCH (p1:Paper), (p2:Paper) WHERE ID(p1) = {id1}' \
                        ' AND ID(p2) = {id2} MERGE (p1)-[:CITES]->(p2)'
                query = query.format(id1=chrono_ids[key], id2=db_id)
                graph.run(query)


assign_citations()













