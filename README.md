# XGBoost-Regression-prediction-f1_score

The objective of this code is to predict the correctness of questions answered by users in a session based solely on the previous information available for that session. The dataset is structured as a time series, where questions and associated data are presented in sequential order, organized into different level segments. The levels are further divided into three segments: 0-4, 5-12, and 13-22. Participants are required to make predictions on the correctness of each question within these segments as they are presented during the session.
This kaggle competition emphasizes the importance of predicting correctly on the hidden test set, which is roughly the same size as the training set. It is noted that the hidden test set may take significantly longer to process compared to the provided test samples. Model performance will be evaluated using the F1 score, a metric that balances precision and recall in binary classification tasks.

For this purpose, I utilized XGBoost, a powerful machine learning algorithm known for its effectiveness. XGBoost's gradient boosting framework enables it to handle both regression and classification tasks with high efficiency. By utilizing the available previous information within each session, XGBoost models were trained to accurately predict the correctness of user responses to questions. The evaluation of the model's performance in this competition is based on the F1 score, which serves as a metric to assess the balance between precision and recall in binary classification tasks.
