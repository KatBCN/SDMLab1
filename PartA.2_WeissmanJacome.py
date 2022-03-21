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


### Keyword generator
def get_keywords():
    db_keywords = ['Data Management', 'Indexing', 'Data Modeling', 'Big Data',
                'Data Processing', 'Data Storage', 'Data Querying']
    ai_keywords = ['Deep Learning', 'Machine Learning','Reinforcement',
                   'Neural Networks', 'Natural Language Processing',
                   'Artificial Intelligence', 'Bayesian Regression']
    sc_keywords = ['High-Performance Computing', 'Supercomputing',
                   'Parallelization','Quantum Computing', 'Cooling',
                   'Chip Architecture', 'GPU Supercomputing']
    keywords = [db_keywords, ai_keywords, sc_keywords]
    return keywords


def random_keywords(kw_set_no, oversample = 30):
    #get keyword sets
    kw_sets = get_keywords()

    #get non-selected sets' positions
    fix_number = kw_set_no % 3
    bad_sets = [x for x in [0,1,2] if x != fix_number]

    #get sets, merge non-selected ones and pool with selected set oversampling
    main = kw_sets[fix_number]
    filling = kw_sets[bad_sets[0]] + kw_sets[bad_sets[1]]
    kw_pool = main * oversample + filling

    #get number of kws and sample
    n = np.random.randint(1, 3)
    assign_list = random.sample(kw_pool, n)

    return assign_list


def load_keywords():
    keywords = get_keywords()
    kw_pool = keywords[0] + keywords[1] + keywords[2]

    for kw in kw_pool:
        graph.run('MERGE (n:Keyword {{topic: \'{}\'}}) '.format(kw))


def assign_keywords():
    jc_paper_df = graph.run('match (n:Paper)-[:PUBLISHED_IN]->()-[]->(jc) '
                          'WHERE (jc:Journal or jc:Conference) '
                          'return ID(n) as paper_id, ID(jc) as jc_id').to_data_frame()
    jc_list = list(jc_paper_df['jc_id'].unique())

    paper_lists = jc_paper_df.groupby('jc_id')['paper_id'].apply(list)

    n = 0
    for journal in jc_list:
        for paper_id in paper_lists[journal]:
            keywords = random_keywords(n)
            for kw in keywords:
                graph.run('MATCH (p:Paper), (k:Keyword) WHERE ID(p) = {paper_id}'
                          ' AND k.topic = \'{kw}\' MERGE (p)-[:DISCUSSES]->(k)'.format(paper_id=paper_id,
                                                                                  kw=kw))
        n += 1

    print('Keywords assigned.')


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


        if cited_db_ids is not None:
            for db_id in cited_db_ids:
                assert db_id != chrono_ids[key]
                query = 'MATCH (p1:Paper), (p2:Paper) WHERE ID(p1) = {id1}' \
                        ' AND ID(p2) = {id2} MERGE (p1)-[:CITES]->(p2)'
                query = query.format(id1=chrono_ids[key], id2=db_id)
                graph.run(query)

    print('Citations assigned.')


### Reviewer generator
def get_keyword_authors(keyword):
    query = 'match (a:Author)-[:WROTE]->(p:Paper)-[:DISCUSSES]->(k:Keyword)' \
            'where k.topic = \'{}\'' \
            ' return distinct a.name as author order by a.name'
    query = query.format(keyword)

    keyword_authors = list(graph.run(query).to_data_frame()['author'])

    return keyword_authors


def get_paper_keywords(paperid):
    query = 'match (n:Paper)-[:DISCUSSES]-> (k:Keyword) where ID(n) = {} ' \
            'return k.topic as keywords'
    query = query.format(paperid)

    paper_keywords = list(graph.run(query).to_data_frame()['keywords'])

    return paper_keywords


def assign_reviewers():
    papers = list(graph.run('match (n:Paper) return ID(n) as paperid').to_data_frame()['paperid'])

    for paper in papers:
        #fetch a paper's related authors by it's keywords
        keywords = get_paper_keywords(paper)
        related_authors = []
        for keyword in keywords:
            kw_authors = get_keyword_authors(keyword)
            related_authors += kw_authors

        #get paper's authors to remove from related authors
        self_authors_query = 'match (a:Author)-[:WROTE]->(p:Paper)' \
                             'where ID(p) = {} return a.name as author'.format(paper)
        self_authors_df = graph.run(self_authors_query).to_data_frame()
        self_authors = list(self_authors_df['author']) if self_authors_df.shape != (0,0) else []

        #get list of potential reviewers and sample it
        potential_reviewers = [i for i in related_authors if i not in self_authors]
        reviewers = random.sample(potential_reviewers, 3)

        #load to database
        for reviewer in reviewers:
            query = 'MATCH (a:Author), (p:Paper) ' \
                    'WHERE a.name = \"{reviewer}\" AND ID(p) = {paper} ' \
                    'MERGE (a)-[:REVIEWED]->(p)'
            query = query.format(reviewer=reviewer, paper=paper)
            graph.run(query)

    print('Reviewers assigned')


### load data into the database
for journal in journals:
    load_journals(journal)
for conf in conferences:
    load_conferences(conf)
for element in journals + conferences:
    create_corresponding_authors(element)

### load and assign keywords to papers
load_keywords()
assign_keywords()

### assign cites
assign_citations()

### assign reviewers
assign_reviewers()




