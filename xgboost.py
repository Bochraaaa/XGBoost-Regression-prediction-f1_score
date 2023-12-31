# -*- coding: utf-8 -*-
"""xgboost.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Dqme6RgG1faTPHhDEk1Dw37ZDrs0F7cq
"""

import pandas as pd
import numpy as np
import gc
from sklearn.model_selection import KFold, GroupKFold
from xgboost import XGBClassifier
from sklearn.metrics import f1_score, make_scorer
from tqdm import tqdm
from sklearn.model_selection import RandomizedSearchCV

data = pd.read_csv("/kaggle/input/predict-student-performance-from-game-play/train.csv",usecols=[0])

data = data['session_id'].groupby(data['session_id']).count()
PIECES = 10
CHUNK = int( np.ceil(len(data)/PIECES) )
reads = []
skips = [0]
for k in range(PIECES):
    a = k*CHUNK
    b = (k+1)*CHUNK
    if b>len(data): b=len(data)
    r = data.iloc[a:b].sum()
    reads.append(r)
    skips.append(skips[-1]+r)
print(f'To avoid memory error, we will read train in {PIECES} pieces of sizes:')
print(reads)

train = pd.read_csv('/kaggle/input/predict-student-performance-from-game-play/train.csv', nrows=reads[0])
print('Train size of first piece:', train.shape )
train.head()

labels = pd.read_csv('/kaggle/input/predict-student-performance-from-game-play/train_labels.csv')
labels['session'] = labels.session_id.apply(lambda x: int(x.split('_')[0]) )
labels['q'] = labels.session_id.apply(lambda x: int(x.split('_')[-1][1:]) )
print( labels.shape )
labels.head()

CATS = ['event_name', 'fqid', 'room_fqid', 'text_fqid', 'text', 'name']
NUMS = ['elapsed_time','level','page','room_coor_x', 'room_coor_y',
        'screen_coor_x', 'screen_coor_y','hover_duration']
EVENTS = ['navigate_click','person_click','cutscene_click','object_click',
          'map_hover','notification_click','map_click','observation_click',
          'checkpoint']

def feature_engineer(train):

    dfs = []
########categorical###############
    for c in CATS:
        tmp = train.groupby(['session_id','level_group'])[c].agg('nunique')
        tmp.name = tmp.name + '_nunique'
        dfs.append(tmp)
###############nums###############
    for c in NUMS:
        tmp = train.groupby(['session_id','level_group'])[c].agg('mean')
        tmp.name = tmp.name + '_mean'
        dfs.append(tmp)
    for c in NUMS:
        tmp = train.groupby(['session_id','level_group'])[c].agg('std')
        tmp.name = tmp.name + '_std'
        dfs.append(tmp)
    for c in NUMS:
        tmp = train.groupby(['session_id', 'level_group'])[c].agg(lambda x: x.max() - x.min())
        tmp.name = tmp.name + '_range'
        dfs.append(tmp)
    for c in NUMS:
        tmp = train.groupby(['session_id', 'level_group'])[c].agg('median')
        tmp.name = tmp.name + '_median'
        dfs.append(tmp)

##############EVENTS list###################""
    for c in EVENTS:
        train[c] = (train.event_name == c).astype('int8')
    for c in EVENTS + ['elapsed_time']:
        tmp = train.groupby(['session_id','level_group'])[c].agg('sum')
        tmp.name = tmp.name + '_sum'
        dfs.append(tmp)
    for c in EVENTS :
        tmp = train.groupby(['session_id', 'level_group'])[c].agg(lambda x: x.mode().values[0])
        tmp.name = tmp.name + '_mode'
        dfs.append(tmp)



    train = train.drop(EVENTS,axis=1)
    df = pd.concat(dfs,axis=1)
    df = df.fillna(-1)
    df = df.reset_index()
    df = df.set_index('session_id')
    return df

# Commented out IPython magic to ensure Python compatibility.
# %%time
# 
# # PROCESS TRAIN DATA IN PIECES
# all_pieces = []
# print(f'Processing train as {PIECES} pieces to avoid memory error... ')
# for k in range(PIECES):
#     print(k,', ',end='')
#     SKIPS = 0
#     if k>0: SKIPS = range(1,skips[k]+1)
#     train = pd.read_csv('/kaggle/input/predict-student-performance-from-game-play/train.csv',
#                         nrows=reads[k], skiprows=SKIPS)
#     df = feature_engineer(train)
#     all_pieces.append(df)
# 
# # CONCATENATE ALL PIECES
# print('\n')
# del train; gc.collect()
# df = pd.concat(all_pieces, axis=0)
# print('Shape of all train data after feature engineering:', df.shape )
# df.head()

FEATURES = [c for c in df.columns if c != 'level_group']
print('We will train with', len(FEATURES) ,'features')
ALL_USERS = df.index.unique()
print('We will train with', len(ALL_USERS) ,'users info')

gkf = GroupKFold(n_splits=5)
oof = pd.DataFrame(data=np.zeros((len(ALL_USERS),18)), index=ALL_USERS)
models = {}
# COMPUTE CV SCORE WITH 5 GROUP K FOLD
for i, (train_index, test_index) in enumerate(gkf.split(X=df, groups=df.index)):
    print('#'*25)
    print('### Fold',i+1)
    print('#'*25)
    xgb_params = {
    'objective' : 'binary:logistic',
    'eval_metric':'logloss',
    'learning_rate': 0.05,
    'max_depth': 4,
    'reg_alpha' : 0.5,
    'reg_lambda' : 0.5,
    'n_estimators': 1000,
    'early_stopping_rounds': 50,
    'tree_method':'hist',
    'subsample':0.8,
    'colsample_bytree': 0.4
    }

    # ITERATE THRU QUESTIONS 1 THRU 18
    for t in range(1,19):

        # USE THIS TRAIN DATA WITH THESE QUESTIONS
        if t<=3: grp = '0-4'
        elif t<=13: grp = '5-12'
        elif t<=22: grp = '13-22'

        # TRAIN DATA
        train_x = df.iloc[train_index]
        train_x = train_x.loc[train_x.level_group == grp]
        train_users = train_x.index.values
        train_y = labels.loc[labels.q==t].set_index('session').loc[train_users]

        # VALID DATA
        valid_x = df.iloc[test_index]
        valid_x = valid_x.loc[valid_x.level_group == grp]
        valid_users = valid_x.index.values
        valid_y = labels.loc[labels.q==t].set_index('session').loc[valid_users]

        # TRAIN MODEL
        clf =  XGBClassifier(**xgb_params)
        clf.fit(train_x[FEATURES].astype('float32'), train_y['correct'],
                eval_set=[ (valid_x[FEATURES].astype('float32'), valid_y['correct']) ],
                verbose=0)
        print(f'{t}({clf.best_ntree_limit}), ',end='')

        # SAVE MODEL, PREDICT VALID OOF
        models[f'{grp}_{t}'] = clf
        oof.loc[valid_users, t-1] = clf.predict_proba(valid_x[FEATURES].astype('float32'))[:,1]

    print()

# PUT TRUE LABELS INTO DATAFRAME WITH 18 COLUMNS
true = oof.copy()
for k in range(18):
    # GET TRUE LABELS
    tmp = labels.loc[labels.q == k+1].set_index('session').loc[ALL_USERS]
    true[k] = tmp.correct.values

scores = []; thresholds = []
best_score = 0; best_threshold = 0

for threshold in np.arange(0.4,0.81,0.01):
    print(f'{threshold:.02f}, ',end='')
    preds = (oof.values.reshape((-1))>threshold).astype('int')
    m = f1_score(true.values.reshape((-1)), preds, average='macro')
    scores.append(m)
    thresholds.append(threshold)
    if m>best_score:
        best_score = m
        best_threshold = threshold

import matplotlib.pyplot as plt

# PLOT THRESHOLD VS. F1_SCORE
plt.figure(figsize=(20,5))
plt.plot(thresholds,scores,'-o',color='blue')
plt.scatter([best_threshold], [best_score], color='blue', s=300, alpha=1)
plt.xlabel('Threshold',size=14)
plt.ylabel('Validation F1 Score',size=14)
plt.title(f'Threshold vs. F1_Score with Best F1_Score = {best_score:.3f} at Best Threshold = {best_threshold:.3}',size=18)
plt.show()

print('When using optimal threshold...')
for k in range(18):

    # COMPUTE F1 SCORE PER QUESTION
    m = f1_score(true[k].values, (oof[k].values>best_threshold).astype('int'), average='macro')
    print(f'Q{k}: F1 =',m)

# COMPUTE F1 SCORE OVERALL
m = f1_score(true.values.reshape((-1)), (oof.values.reshape((-1))>best_threshold).astype('int'), average='macro')
print('==> Overall F1 =',m)