import ast

from neo4j import GraphDatabase

import numpy as np
import pandas as pd

import sklearn.metrics
from sklearn.decomposition import PCA
from sklearn import svm
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.metrics import plot_confusion_matrix

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns

import py2neo

np.random.seed(42)


# Initialize and test connection
uri = 'bolt://localhost:7687',
pwd = '1234katmat'

conn = py2neo.Graph("bolt://localhost:7687", user='neo4j', password='1234katmat')


print(conn.query("MATCH (n) RETURN COUNT(n)"))

# create constraint
query = """CREATE CONSTRAINT papers IF NOT EXISTS ON (p:Paper) ASSERT p.id IS UNIQUE"""
conn.run(query)

# create in-memory graph


query = """CALL gds.graph.create('for_embeddings','Paper',{CITES:{orientation: 'UNDIRECTED'}})"""

# conn.run(query)


# create embeddings
def create_embs(dim=10):

    query = """CALL gds.fastRP.write(
               'for_embeddings',
               {
                   embeddingDimension: %d,
                   iterationWeights: [0.0, 0.0, 1.0, 1.0],
                   writeProperty: 'fastrp_embedding'
               }
           )
    """ % (dim)

    conn.run(query)
    return


# separate target and predictors
def create_X_y():

    query = """MATCH (p:Paper) RETURN p.id AS id, p.access AS access, p.fastrp_embedding AS fastrp_embedding"""
    emb_df = pd.DataFrame([dict(_) for _ in conn.run(query)])
    emb_df = emb_df.loc[emb_df['access'] != "Editorship"]
    emb_df['target'] = pd.factorize(emb_df['access'])[0].astype("float32")
    emb_df = emb_df.loc[emb_df['target'] != -1.0]
    y = emb_df['target'].to_numpy()
    emb_df['X'] = emb_df['fastrp_embedding'].apply(lambda x: np.array(x))
    X = np.array(emb_df['X'].to_list())

    return X, y


# modeler function
def model(dim, k_folds=5, model='linear', show_matrix=True, show_PCA=True):
    acc_scores = []

    create_embs(dim=dim)
    X, y = create_X_y()

    for i in range(0, k_folds):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25)
        clf = svm.SVC(kernel='rbf', class_weight={0.0:20, 1.0:1}) #give more weight to open acces papers because they're less frequent
        clf.fit(X_train, y_train)
        pred = clf.predict(X_test)

        acc = accuracy_score(pred, y_test)
        acc_scores.append(acc)

    print('Accuracy scores: ', acc_scores)
    print('Mean accuracy: ', np.mean(acc_scores))

    if show_matrix:
        matrix = sklearn.metrics.ConfusionMatrixDisplay.from_estimator(clf, X_test, y_test,
                                                                       cmap=plt.cm.Blues, normalize='true',
                                                                       display_labels = ["Open Access", "Subscription"])
        plt.show()

    if show_PCA:
        pca = PCA(n_components=2)
        print(X_train)
        lst = pca.fit_transform(X_train)
        print(lst)

        x_lst = []
        y_lst = []
        for point in lst:
            x_lst.append(point[0])
            y_lst.append(point[1])

        df = pd.DataFrame(columns=["PC1","PC2","class"])
        df["PC1"] = x_lst
        df["PC2"] = y_lst

        class_dict = {0.0:"Open Access", 1.0:"Subscription"}
        df["class"] = y_train

        print(df)

        plot_n = 500
        plt.scatter(df["PC1"][:plot_n], df["PC2"][:plot_n], c=df["class"][:plot_n], cmap='coolwarm', alpha = 0.8)
        plt.xlabel("PC1")
        plt.ylabel("PC2")
        plt.title("Embeddings PCA")
        plt.show()

    return


model(dim=500)