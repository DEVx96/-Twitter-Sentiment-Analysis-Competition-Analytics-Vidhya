# -*- coding: utf-8 -*-
"""Identify_the_Sentiments.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/142I4fy5PtayHasvcaNwgfP3xL56qHVIY
"""

# Commented out IPython magic to ensure Python compatibility.
# %reload_ext autoreload
# %autoreload 2
# %matplotlib inline
from fastai import *
from fastai.text import  *
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
import torch.nn as nn
from tqdm.notebook import tqdm
import transformers
from transformers import BertForSequenceClassification,BertTokenizer,AdamW,get_linear_schedule_with_warmup
from torch.utils.data import TensorDataset,DataLoader,RandomSampler,SequentialSampler
import random

df = pd.read_csv('/content/train_2kmZucJ.csv',)
df.head()

df['label'].value_counts()

idx_train,idx_val,_,_ = train_test_split(df.index.values,df.label.values,test_size=0.15,random_state=10,stratify = df.label.values)
df['data_type'] = ['na']*df.shape[0]
df.loc[idx_train,"data_type"] = 'train'
df.loc[idx_val,"data_type"] = 'val'
idx_train[:10]

df.data_type.value_counts(), df[df['data_type'] == 'val']['label'].value_counts()

df.head()

tweets = TextList.from_csv('/content','train_2kmZucJ.csv',cols='tweet').split_by_idxs(idx_train,idx_val).label_from_df(cols=1)
tweets

tweets.train.x[1].text,tweets.train.x[1], tweets.train.y[1]

len(tweets.vocab.itos)

def doc_matrix_csr(text_list,n_terms):
  
  values = []
  column_ids = []
  row_pointer = []
  row_pointer.append(0)

  for _,doc in enumerate(text_list):
    feature_counter = Counter(doc.data)
    column_ids.extend(feature_counter.keys())
    values.extend(feature_counter.values())
    row_pointer.append(len(values))
  
  return scipy.sparse.csr_matrix((values,column_ids,row_pointer), shape = (len(row_pointer)- 1,n_terms),dtype=int)

train_doc_term = doc_matrix_csr(tweets.train.x,len(tweets.vocab.itos))
val_doc_term = doc_matrix_csr(tweets.valid.x,len(tweets.vocab.itos))
train_doc_term,val_doc_term

vectorizer = CountVectorizer(preprocessor=noop, tokenizer=noop, max_features=800000)
train_docs = tweets.train.x
train_words = [[tweets.vocab.itos[o] for o in doc.data] for doc in train_docs]
train_doc_mat = vectorizer.fit_transform(train_words)
train_doc_mat

valid_docs = tweets.valid.x
valid_words = [[tweets.vocab.itos[o] for o in doc.data] for doc in valid_docs]
val_doc_mat = vectorizer.transform(valid_words)
val_doc_mat

"""### **Naive Bayes**"""

y_train = tweets.train.y.items
y_val = tweets.valid.y.items
x = train_doc_mat
x_val = val_doc_mat

#Train
p = (y_train ==  1).mean()
q = (y_train == 0).mean()
b = np.log(p/q)
print('bias : ',b)

C0 = np.squeeze(np.asarray(x[y_train == 0].sum(0)))
C1 = np.squeeze(np.asarray(x[y_train == 1].sum(0)))
L0 = (C0 + 1)/ ((y_train == 0).sum() + 1)
L1 = (C1 + 1)/ ((y_train == 1).sum() + 1)
R = np.log(L1/L0)
print('R: ',R)

preds_tr_freq = b + x@R > 0
pred_acc_freq = (preds_tr_freq == y_train).mean()

w = x.sign()
preds_tr = b + w@R > 0
pred_acc = (preds_tr == y_train).mean()

#Val

preds_val_freq = b + x_val@R > 0
val_acc_freq = (preds_val_freq == y_val).mean()

w_val = x_val.sign()
preds_val = b + w_val@R > 0
val_acc = (preds_val == y_val).mean()

print('train accuracy when considering frequency of occurence:  ',pred_acc_freq*100,'%','\n','train accuracy without considering frequency of occurence:  ',pred_acc*100,'%')
print('val accuracy when considering frequency of occurence:  ',val_acc_freq*100,'%','\n','val accuracy without considering frequency of occurence:  ',val_acc*100,'%')

tfidf_vectorizer = TfidfVectorizer(preprocessor=noop, tokenizer=noop, max_features=800000)
train_tfidf = tfidf_vectorizer.fit_transform(train_words)
val_tfidf = tfidf_vectorizer.transform(valid_words)
train_tfidf ,val_tfidf

x_tf_tr = train_tfidf
x_tf_val = val_tfidf

#Train
C0_tf = np.squeeze(np.asarray(x_tf_tr[y_train == 0].sum(0)))
C1_tf = np.squeeze(np.asarray(x_tf_tr[y_train == 1].sum(0)))
L0_tf = (C0_tf + 1)/ ((y_train == 0).sum() + 1)
L1_tf = (C1_tf + 1)/ ((y_train == 1).sum() + 1)
R_tf = np.log(L1_tf/L0_tf)
print('R: ',R_tf)

tf_tr = b + x_tf_tr @R_tf > 0
tf_acc = (tf_tr == y_train).mean()

#Val

tf_val = b + x_tf_val@R > 0
tf_val_acc = (tf_val == y_val).mean()

print('train accuracy using tfidf:  ',tf_acc*100,'%')
print('val accuracy using tfidf:  ',tf_val_acc*100,'%')

"""### **Logistic Regression**"""

log_reg = LogisticRegression()
param_grid= {'C':[1,0.1,0.01],'solver':['liblinear','lbfgs']}
grid = GridSearchCV(log_reg,param_grid=param_grid,cv=5,verbose=0)
grid.fit(train_tfidf,y_train)
print(grid.best_estimator_)
log_reg = grid.best_estimator_

x_list = [train_doc_mat, train_doc_mat.sign(), train_tfidf]
x_val_list = [val_doc_mat, val_doc_mat.sign(), val_tfidf]
accuracy = [] # (train,val,train) as tuples_
for i in range(len(x_list)):
  log_reg.fit(x_list[i],y_train)
  acc_1 = (log_reg.predict(x_list[i]) == y_train).mean()*100
  acc_2 = (log_reg.predict(x_val_list[i]) == y_val).mean()*100
  accuracy.append((acc_1,acc_2))

accuracy ,# count_vector, count_vector (No freq), tfidf

"""highest accuracy with tfidf

## **Transfer Learning**
"""

df_test = pd.read_csv('test_oJQbWVk.csv')
df_test.head(),df_test.shape

df_complete = pd.concat([df[['tweet']],df_test[['tweet']]])
assert df_complete.shape[0] == (df.shape[0] + df_test.shape[0])
df_complete.head(),df_complete.shape

"""### Forward Model"""

data_lm = TextList.from_df(df=df_complete).split_by_rand_pct(0.1).label_for_lm().databunch(bs=48)

data_lm.show_batch()

learn_lm = language_model_learner(data_lm,AWD_LSTM,drop_mult=0.2)
learn_lm.lr_find()
learn_lm.recorder.plot()

learn_lm.fit_one_cycle(2,1e-01,moms=(0.8,0.7))

learn_lm.unfreeze()
learn_lm.lr_find()
learn_lm.recorder.plot()

learn_lm.fit_one_cycle(1,1e-03,moms=(0.8,0.7))
learn_lm.save('lm_1')

learn_lm.fit_one_cycle(1,1e-03,moms=(0.8,0.7))
learn_lm.save('lm_2')

learn_lm.fit_one_cycle(1,1e-03,moms=(0.8,0.7))
learn_lm.save('lm_3')

learn_lm.fit_one_cycle(1,1e-03,moms=(0.8,0.7))
learn_lm.save('lm_4')

learn_lm.fit_one_cycle(1,1e-03,moms=(0.8,0.7))
learn_lm.save('lm_5')

learn_lm.fit_one_cycle(1,1e-03,moms=(0.8,0.7))
learn_lm.save('lm_6')

learn_lm.fit_one_cycle(1,1e-03,moms=(0.8,0.7))
learn_lm.save('lm_7')

learn_lm.load('lm_5')
learn_lm.save_encoder('learn_enc')
learn_lm.data.vocab.save('vocab.pkl')

learn_lm.summary()

data_cls = TextList.from_df(df,vocab=data_lm.vocab,cols='tweet').split_by_idxs(idx_train,idx_val).label_from_df(cols=1).databunch(bs=48)

data_cls.show_batch()

learn_cls = text_classifier_learner(data_cls,AWD_LSTM,drop_mult=0.4)

learn_cls.summary()

learn_cls.load_encoder('learn_enc')
pass

learn_cls.lr_find()
learn_cls.recorder.plot(skip_end = 10)

learn_cls.fit_one_cycle(1,6e-02,moms = (0.8,0.7))
learn_cls.save('cls_1')

learn_cls.freeze_to(-2)
learn_cls.lr_find()
learn_cls.recorder.plot()

learn_cls.fit_one_cycle(1,slice(1e-02/(2.6**4),1e-02),moms=(0.7,0.8))

learn_cls.freeze_to(-3)
learn_cls.lr_find()
learn_cls.recorder.plot()

learn_cls.fit_one_cycle(1,slice(2e-02/(2.6**4),2e-02),moms=(0.8,0.7))

learn_cls.unfreeze()
learn_cls.lr_find()
learn_cls.recorder.plot()

learn_cls.fit_one_cycle(2,slice(2e-03/(2.6**4),2e-03),moms=(0.7,0.8))

learn_cls.save('cls_2')

learn_cls.fit_one_cycle(1,slice(2e-03/(2.6**4),2e-03),moms=(0.7,0.8))

learn_cls.save('cls_3')

preds_train,tr_targ = learn_cls.get_preds(ds_type = DatasetType.Train.value,ordered=True)
(np.argmax(preds_train,axis=1) == tr_targ).float().mean()*100

learn_cls.load('cls_3')
pass

"""### Backwards Model"""

data_lm_bwd = TextList.from_df(df=df_complete).split_by_rand_pct(0.1).label_for_lm().databunch(bs=48,backwards=True)
data_lm_bwd.show_batch()

learn_lm_bwd = language_model_learner(data_lm_bwd,AWD_LSTM,drop_mult=0.2)
learn_lm_bwd.lr_find()
learn_lm_bwd.recorder.plot()

learn_lm_bwd.fit_one_cycle(2,1e-01,moms=(0.8,0.7))

learn_lm.unfreeze()
learn_lm.lr_find()
learn_lm.recorder.plot()

learn_lm_bwd.fit_one_cycle(5,1e-03,moms=(0.8,0.7))
learn_lm_bwd.save('lm_bwd')

learn_lm_bwd.save_encoder('learn_bwd_enc')

data_cls_bwd = TextList.from_df(df,vocab=data_lm_bwd.vocab,cols='tweet').split_by_idxs(idx_train,idx_val).label_from_df(cols=1).databunch(bs=48,backwards=True)

learn_cls_bwd = text_classifier_learner(data_cls_bwd,AWD_LSTM,drop_mult=0.4)
learn_cls_bwd.load_encoder('learn_bwd_enc')
learn_cls_bwd.lr_find()
learn_cls_bwd.recorder.plot(skip_end = 10)

learn_cls_bwd.fit_one_cycle(1,6e-02,moms = (0.8,0.7))

learn_cls_bwd.freeze_to(-2)
learn_cls_bwd.lr_find()
learn_cls_bwd.recorder.plot()

learn_cls_bwd.fit_one_cycle(1,slice(1e-02/(2.6**4),1e-02),moms=(0.7,0.8))

learn_cls_bwd.freeze_to(-3)
learn_cls_bwd.lr_find()
learn_cls_bwd.recorder.plot()

learn_cls_bwd.fit_one_cycle(1,slice(2e-02/(2.6**4),2e-02),moms=(0.8,0.7))

learn_cls_bwd.unfreeze()
learn_cls_bwd.lr_find()
learn_cls_bwd.recorder.plot()

learn_cls_bwd.fit_one_cycle(2,slice(2e-03/(2.6**4),2e-03),moms=(0.7,0.8))

learn_cls_bwd.save('cls_bwd_2')

preds_bwd_train,tr_targ = learn_cls_bwd.get_preds(ds_type = DatasetType.Train.value,ordered=True)
(np.argmax(preds_bwd_train,axis=1) == tr_targ).float().mean()*100

#Backwards = 90.65 %
#Forwards = 90.90%

"""### Ensemble"""

preds,targs = learn_cls.get_preds(ordered=True)
(np.argmax(preds,axis=1) == targs).float().mean()*100

preds_bwd,targs = learn_cls_bwd.get_preds(ordered=True)
(np.argmax(preds_bwd,axis=1) == targs).float().mean()*100

preds_avg = (preds+preds_bwd)/2
(np.argmax(preds_avg,axis=1) == targs).float().mean()*100

#about 91.246%

"""## **BERT**"""

df.head()

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased',do_lower_case = True)

encoded_data_train = tokenizer.batch_encode_plus(df[df.data_type == 'train'].tweet.values,
                                                 add_special_tokens = True,
                                                 return_attention_mask=True,
                                                 pad_to_max_length =True,
                                                 max_length = 300, #Max Characters in a tweet
                                                 return_tensors = 'pt',
                                                 ) 

encoded_data_val = tokenizer.batch_encode_plus(df[df.data_type == 'val'].tweet.values,
                                                 add_special_tokens = True,
                                                 return_attention_mask=True,
                                                 pad_to_max_length =True,
                                                 max_length = 300, #Max Characters in a tweet
                                                 return_tensors = 'pt',
                                                 ) 

input_ids_train = encoded_data_train['input_ids']
attention_mask_train = encoded_data_train['attention_mask']
label_train = torch.tensor(df[df.data_type == 'train'].label.values)

input_ids_val = encoded_data_val['input_ids']
attention_mask_val = encoded_data_val['attention_mask']
label_val = torch.tensor(df[df.data_type == 'val'].label.values)

dataset_train = TensorDataset(input_ids_train,attention_mask_train,label_train)
dataset_val = TensorDataset(input_ids_val,attention_mask_val,label_val)

model = BertForSequenceClassification.from_pretrained("bert-base-uncased",num_labels=2,
                                                      output_attentions=False,output_hidden_states=False)

bs = 32
dataloader_train = DataLoader(dataset_train,sampler=RandomSampler(dataset_train),batch_size=bs)
dataloader_val = DataLoader(dataset_val,sampler = SequentialSampler(dataset_val),batch_size=bs)

epochs = 4
optimizer = AdamW(model.parameters(),lr = 3e-05,eps=1e-07)
scheduler = get_linear_schedule_with_warmup(optimizer,num_warmup_steps=0,
                                            num_training_steps= len(dataloader_train)*epochs)

def accuracy(preds,labels):
  preds_flat = np.argmax(preds,axis=1).flatten()
  labels_flat = labels.flatten()
  return (preds_flat == labels_flat).mean()

seed_val = 10
random.seed(seed_val)
np.random.seed(seed_val)
torch.manual_seed(seed_val)
torch.cuda.manual_seed_all(seed_val)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)
print(device)

def evaluate(dataloader):
  model.eval()
  loss_val_total = 0
  preds,true_labels = [],[]
  
  for batch in dataloader:
    batch = tuple(b.to(device) for b in batch)
    inputs  = {'input_ids': batch[0], 'attention_mask' : batch[1], 'labels' : batch[2] }
    with torch.no_grad():
      outputs = model(**inputs)
    
    loss = outputs[0]
    logits = outputs[1]
    loss_val_total += loss.item()

    logits = logits.detach().cpu().numpy()
    label_ids = inputs['labels'].detach().cpu().numpy()
    preds.append(logits)
    true_labels.append(label_ids)
  
  loss_val_avg = loss_val_total/len(dataloader_val) 
    
  preds = np.concatenate(preds, axis=0)
  true_labels = np.concatenate(true_labels, axis=0)
            
  return loss_val_avg, preds, true_labels

for epoch in tqdm(range(1, epochs+1)):

  model.train()

  loss_train_total = 0

  progress_bar = tqdm(dataloader_train,desc='Epoch {:1d}'.format(epoch),leave=False,disable=False)

  for batch in progress_bar:
    model.zero_grad()
    batch = tuple(b.to(device) for b in batch)
    inputs = {'input_ids': batch[0],'attention_mask': batch[1],'labels': batch[2]}
    outputs = model(**inputs)

    loss= outputs[0]
    loss_train_total += loss.item()
    loss.backward()

    nn.utils.clip_grad_norm_(model.parameters(),1.0)

    optimizer.step()
    scheduler.step()
    
    progress_bar.set_postfix({'training_loss': '{:.3f}'.format(loss.item()/len(batch))})
    
  torch.save(model.state_dict(), f'finetuned_BERT_epoch_{epoch}.model')
  tqdm.write(f'\nEpoch {epoch}')

  loss_train_avg = loss_train_total/len(dataloader_train)            
  tqdm.write(f'Training loss: {loss_train_avg}')
    
  val_loss, preds, true_labels = evaluate(dataloader_val)
  val_acc = accuracy(preds,true_labels)
  tqdm.write(f'Validation loss: {val_loss}')
  tqdm.write(f'Accuracy Score : {val_acc}')

tr_loss, tr_preds, true_labels = evaluate(dataloader_train)
tr_acc = accuracy(tr_preds,true_labels)
tr_acc

"""# Test"""

df_test.head()

df_sample = pd.read_csv('sample_submission_LnhVWA4.csv',index_col='id')
df_sample.head()

"""### Naive Bayes"""

tweets_test = TextList.from_df(df_test,cols='tweet',vocab=tweets.vocab).split_none().label_empty()
tweets_test

len(tweets_test.vocab.itos)

test_docs = tweets_test.train.x
test_words = [[tweets_test.vocab.itos[o] for o in doc.data] for doc in test_docs]
test_doc_mat = vectorizer.transform(test_words)
test_doc_tfidf = tfidf_vectorizer.transform(test_words)

x_test = test_doc_mat
w_test = test_doc_mat.sign()
test_nb_occ = (b + w_test@R > 0)*1
test_nb_cv =  (b + x_test@R > 0)*1
test_nb_tf = (b + test_doc_tfidf@R_tf > 0)*1
len(test_nb_tf),len(test_nb_cv)

df_sample['label'] = test_nb_cv
df_sample.to_csv('cv_NB')

df_sample['label'] = test_nb_occ
df_sample.to_csv('occ_NB')

df_sample['label'] = test_nb_tf
df_sample.to_csv('tf_NB')

df_sample.head()

"""### Logistic Regression"""

x_test_list = [test_doc_mat, val_doc_mat.sign(), test_doc_tfidf]
preds_list = []
for a in range(len(x_list)):
  log_reg.fit(x_list[i],y_train)
  preds_list.append(log_reg.predict(x_test_list[i]))

df_sample['label'] = preds_list[0]
df_sample.to_csv('cv_LR')

df_sample['label'] = preds_list[1]
df_sample.to_csv('occ_LR')

df_sample['label'] = preds_list[2]
df_sample.to_csv('tf_LR')

"""### AWD_LSTM"""

tweets_tst = TextList.from_df(df_test,cols='tweet')

data_cls = TextList.from_df(df,vocab= data_lm.vocab,cols='tweet').split_by_idxs(idx_train,idx_val).label_from_df(cols=1).add_test(tweets_tst).databunch(bs=48)

learn_cls = text_classifier_learner(data_cls,AWD_LSTM,drop_mult=0.4)
learn_cls.load('cls_3')
pass

preds_fwd_,_ = learn_cls.get_preds(ds_type= DatasetType.Test,ordered=True)
preds_fwd = preds_fwd_.numpy()
preds_fwd = np.argmax(preds_fwd,axis=1)

data_cls_bwd = TextList.from_df(df,vocab=data_lm_bwd.vocab,cols='tweet').split_by_idxs(idx_train,idx_val).label_from_df(cols=1).add_test(tweets_tst).databunch(bs=48,backwards=True)

learn_cls_bwd = text_classifier_learner(data_cls_bwd,AWD_LSTM,drop_mult=0.4)

learn_cls_bwd.load('cls_bwd_2')
pass

preds_bwd_,_ = learn_cls_bwd.get_preds(ds_type= DatasetType.Test,ordered=True)
preds_bwd = preds_bwd_.numpy()
preds_bwd = np.argmax(preds_bwd,axis=1)

preds_ensemble = (preds_bwd_+preds_fwd_)/2
preds_ensemble = preds_ensemble.numpy()
preds_ensemble = np.argmax(preds_ensemble,axis=1)

df_sample['label'] = preds_fwd
df_sample.to_csv('LSTM_fwd.csv')

df_sample['label'] = preds_bwd
df_sample.to_csv('LSTM_bwd.csv')

df_sample['label'] = preds_ensemble
df_sample.to_csv('LSTM_ens.csv')

"""### BERT"""

encoded_data_test = tokenizer.batch_encode_plus(df_test.tweet.values,
                                                 add_special_tokens = True,
                                                 return_attention_mask=True,
                                                 pad_to_max_length =True,
                                                 max_length = 300, #Max Characters in a tweet
                                                 return_tensors = 'pt',
                                                 ) 

input_ids_test = encoded_data_test['input_ids']
attention_mask_test = encoded_data_test['attention_mask']
dataset_test = TensorDataset(input_ids_test,attention_mask_test)

dataloader_test = DataLoader(dataset_test,sampler=SequentialSampler(dataset_test),batch_size=48)

model = BertForSequenceClassification.from_pretrained("bert-base-uncased",num_labels=2,
                                                      output_attentions=False,output_hidden_states=False)

model.load_state_dict(torch.load('/content/finetuned_BERT_epoch_2.model'))
model = model.to(device)

def predict(dataloader):
  model.eval()
  loss_test_total = 0
  preds = []

  for batch in dataloader:
    batch = tuple(b.to(device) for b in batch) 
    inputs = {
              "input_ids" : batch[0],
              "attention_mask" : batch[1]
              }
    
    with torch.no_grad():
      outputs = model(**inputs)
    
    logits = outputs[0]
    logits = logits.detach().cpu().numpy()
    preds.append(logits)
  
  preds = np.concatenate(preds,axis=0)
 
  return preds

test_preds=  predict(dataloader_test)

test_preds_flat = np.argmax(test_preds,axis=1).flatten()
test_preds_flat[:5]

df_sample['label'] = test_preds_flat
df_sample.to_csv('Bert.csv')

"""# Results"""

pd.read_excel('Results.xlsx')