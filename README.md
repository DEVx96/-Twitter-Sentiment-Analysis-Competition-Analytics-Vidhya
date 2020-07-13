# Twitter Sentiment Analysis Competition

# Problem Statement
Sentiment analysis remains one of the key problems that has seen extensive application of natural language processing. This time around, given the tweets from customers about various tech firms who manufacture and sell mobiles, computers, laptops, etc, the task is to identify if the tweets have a negative sentiment towards such companies or products.

# Data Description
For training the models, a labelled tweets dataset is provided. The dataset is provided in the form of a csv file with each line storing a tweet id, its label and the tweet. The test data file contains only tweet ids and the tweet text with each tweet in a new line.

# Dataset
- train.csv: 7,920 tweets
- test.csv: 1,953 tweets,
* Link to competition : https://datahack.analyticsvidhya.com/contest/linguipedia-codefest-natural-language-processing-1  

# Aim
The performances of different models ranging from computationally fast shallow learning algoriths like Naive Bayes, Logistic Regression to more complex models like a LSTM and transformers.

# Approach

## Naive Bayes and Logistic Regression
* The tweets were tokenized using spacy's tokenization approach. The tokens were then embedded using count vectorization, occurence vectors and TFIDF vectorization before feeding to the shallow learning algorithm
## ULMFit
- After spacy tokenization, transfer learning using Fastai's ULMfit approach was used to predict the sentiments
## Pre-Trained BERT
- Pre-Trained BERT tokens from HuggingFace was used to tokenize the tweets. The model was then trained and it achieved rank 19 on the hackathon.
# Results
![alt tag](https://user-images.githubusercontent.com/54212042/87355122-6f78e800-c57d-11ea-9cb8-8bf97c795813.png)
