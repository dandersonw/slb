
Semantic Scholar uses Elasticsearch as the core component in the search engine.
Naturally we needed a query,
so we hand crafted one that did a serviceable job.
About six months ago we embarked on an effort to improve search relevance 
but encountered difficulty making the changes we wanted
with the functionality available out of the box in Elasticsearch. 
We therefore developed a plugin to extend that functionality 
to include a more normalized machine learning environment.

# The Problem

If we look at an official
ES
[guide](https://www.elastic.co/guide/en/elasticsearch/guide/current/controlling-relevance.html) to
improving search relevance we can see what is available out of the box. Most of
what is available centers around two things: matching multiple fields (title,
abstract), and matching in multiple ways (phrase, bigram). These are ways to get
different numerical features describing the document and its match with the
query. That's great - we want all the information we can get.

```javascript
"bool": {
    "should": [
        {
            "match": {
                "title": "Deep Learning"
            }
        },
        {
            "match": {
                "title.bigram": "Deep Learning"
            }
        }
    ]
}
```


A problem arises when we have all this information though. How do we take in
different features and combine them into a final score? The essential
Elasticsearch technique is to write your query as a tree with similar features
grouped together. This allows you to attempt to tune your query by coming up
with better combinations of subtrees or transformations on subtree scores
(e.x. exponentiation). 

```javascript
"bool": {
    "should": [
        {
            "match": {
                "boost": 5.0,
                "title": "Deep Learning"
            }
        },
        {
            "match": {
                "abstract": "Deep Learning"
            }
        }
    ]
}
```


That is fine as far as it goes - but it does not go as far as we would
like. That is, we cannot write the arbitrary models we want. We can write custom
scoring scripts, but they get only one `_score` value - they cannot see how much
of the score came from `title` 
and how much came from `abstract`.
Without visibility into individual feature values
it is not clear how to express something like a decision tree.
Furthermore,
even if a script could see multiple values
it is not clear how to train a model
with this setup.

# The Solution - a plugin!

The high level goal of our plugin is to enable a normalized learning to rank
workflow with Elasticsearch at the core. 
We implement a Lucene `Query` that iterates over documents that match a query,
and captures the values of low-level features 
from matching the query to the document.
The features are collected 
and can be sent to an arbitrary scoring function
to compute the final document score,
or sent over the wire for use by an offline system.

Instead of writing a plugin to provide a modified `Query`, 
we could have written a service to take a large sample
(say 1000 documents)
from a basic Elasticsearch query
and rank the documents again. 
This would have been nice 
because it would not have complicated our Elasticsearch deployment
and we could calculate even the most expensive of features.
With the plugin we have to redeploy whenever we make changes,
and features that are evaluated on many documents need to be cheap.
On the other hand, 
we believed that the plugin would be
the more performant final solution
given cheap features,
and its integration into Elasticsearch 
meant the overall system architecture would be simpler.
Ultimately we decided in favor of the plugin model 
because of the conceptual simplicity
and its composability with reranking in the worst case.

## Feature templates

Features templates are specifications for the features to calculate and pass to
a model. Features are implemented by wrapping and capturing the results of
normal Lucene queries and scripts. This made sense for us because it allows the
use of the wealth of preexisting functionality without a lot of implementation
cost.

```javascript
"features": [
                {
                    "name": "FEATURE_NAME",
                    "FEATURE_TYPE": {
                        FEATURE_CONTENT
                    }
                }
                ...
            ]
```

An example of a feature:

```javascript
{
    "name": "keyPhrases",
    "query": {
        "match": {
            "keyPhrases": {
                "query": "#query",
            }
        }
    }
}
```

The above will return one value: the score on the match between the query and
the `keyPhrases` field in a document.

Normal queries make use of something called the
[Lucene Practical Scoring Function](https://www.elastic.co/guide/en/elasticsearch/guide/current/practical-scoring-function.html)
which incorporates several lower-level features
(such as TF and DF).
We also implement a featurization wrapper 
that extracts some of those lower-level inputs
and then reports them as features that the model
can learn its own scoring function on.



```javascript
{
    "name": "keyPhrases",
    "finer_query": { <-- Calling a different feature type
        "match": {
            "keyPhrases": {
                "query": "#query",
            }
        }
    }
}
```

The above will return 4 values: the score, the number of matching terms, and the
sums of those terms' TF and DF.

We access numeric fields with simple call outs to scripts:
```javascript
{
    "name": "recency",
    "script": {
        "inline": "doc['year'].value",
        "lang": "expression"
    }
}
```

## Arbitrary scoring functions

With features collected into vectors 
we can write our ranker as a function 
that takes an array of floats and returns a single float
(the score for the document). 
To decide on actual implementation we considered a few factors. 
Firstly, we were using [RankLib](https://sourceforge.net/p/lemur/wiki/RankLib/)'s 
implementation of several models. 
Secondly, we needed as much runtime performance as possible for production. 
Lastly, we also wanted to be able to reload models for rapid experimentation
without restarting the cluster.

To meet the competing demands of production and rapid experimentation we
implemented two ways of providing models. The first is just calling out
serialized RankLib models by filename - the models are loaded and fed data in
the RankLib format. Calling out filenames met the rapid experimentation use case
because we can `scp` models onto the cluster without restarting or recompiling
anything.

RankLib normally evaluates models sort of as an interpreter - it has the model
parameters in a data structure and traverses the data structure. In order to
improve the performance of evaluating models in production we compiled RankLib
regression trees to Java code. 
We distribute these in the plugin binary 
and then call them out by classname.

Calling to a compiled model:

```javascript
{
    "scorer": {
        "name": "Class",
        "params": {
            "class_name": "org.allenai.s2.relevance.scoring.models.LambdaMART"
        }
    }
}
```

A snippet from the included compiled model:

```java
public class LambdaMART implements DocumentScorer {

    public float scoreDocument(FeatureData featureData) {
        return scoreIt(featureData.getFeatureValues());
    }

    private float scoreIt(float[] featureVector) {
        float total;
        total = 0.0f;
        total += 0.1f * scoreIt1(featureVector);
        ...
    }
    
    private float scoreIt1(float[] featureVector) {
        if (featureVector[48] <= 3.4045267f) {
            if (featureVector[7] <= 0.023367213f) {
                if (featureVector[35] <= 0.43057874f) {
                    return -1.2964033f;
                } else {
                    return 0.4352764f;
                }
            } else {
        ...
}
    
```

## Scraping and storing offline

The point of the plugin is to enable a normal machine learning workflow so it
needs to support training (without a cluster running) on the same data as
available at runtime. To enable this we add a REST endpoint to the Elasticsearch
cluster that takes a query with document IDs specified and returns a map from
the document ID to the document's feature vector. Thus the cluster is needed to
turn (document ID, query, label) triples into (feature vector, query, label)
triples but not to learn the (feature vector) -> score model.


## Performance

One potential issue is that by default the feature and model based query is
purely disjunctive - if any feature fires for a document it would run the whole
model on it. The first step was to do something we already did in our baseline -
to filter out documents that didn't contain some match for all mandatory terms
in the query. The second was to tightly tune the implementation of featurization
and model evaluation to be as performant as possible.

Tuning the performance of featurization was actually quite difficult. This
difficulty was connected with difficulty experienced in writing the
featurization code in the first place - the web of Lucene contracts and possible
Elasticsearch calling patterns meant it was easy to experience hard to debug
problems. The solution was to faithfully adhere to the contracts of the Lucene
components touched on and to implement all of the optional functionality
available.

After the performance work was finished the new ranker performed with limited
degradation against the baseline (load tests against the Semantic Scholar search
endpoint measured 10% increase in latency at p99). We were happy to avoid making
any difficult decisions about changing our retrieval model to included reranking
or tightening our filter.

# Conclusion

The development of the plugin and a set of offline training tools
creates a powerful learning to rank environment based on Elasticsearch.
The primary fruit of the plugin, 
and other relevance work that will be discussed in future posts,
is the ability to train rankers easily.
This includes ranker optimized for different query or corpus distributions.
We retrained recently
with the introduction of many new medical papers to Semantic Scholar,
and will continue to adapt our ranking as we expand Semantic Scholar
to include more and more branches of science.
