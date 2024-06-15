import numpy as np
import pandas as pd
from hmmlearn import hmm
from sklearn.model_selection import KFold

def optimize_hmm(X, max_states=10, n_splits=5, n_iter=100):
    best_score = float('-inf')
    best_model = None
    best_n_states = 0
    
    for n_states in range(1, max_states + 1):
        scores = []
        kf = KFold(n_splits=n_splits)
        
        for train_index, test_index in kf.split(X):
            X_train, X_test = X[train_index], X[test_index]
            
            model = hmm.MultinomialHMM(n_components=n_states, n_iter=n_iter)
            model.fit(X_train)
            score = model.score(X_test)
            scores.append(score)
        
        avg_score = np.mean(scores)
        
        if avg_score > best_score:
            best_score = avg_score
            best_model = model
            best_n_states = n_states
            
    return best_model, best_score, best_n_states

def forecast_hmm(model, n_weeks=20):
    _, simulated_states = model.sample(n_weeks)
    simulated_states = simulated_states.flatten()
    return simulated_states

def process_dataframe(df, cat_columns, max_states=10, n_splits=5, n_iter=100):
    results = []
    scores_dict = {}
    n_states_dict = {}
    
    for col in cat_columns:
        print(f"Processing {col}...")
        
        df[col] = df[col].astype('category').cat.codes
        categories = df[col].astype('category').cat.categories
        X = df[col].values.reshape(-1, 1)
        
        best_model, best_score, best_n_states = optimize_hmm(X, max_states, n_splits, n_iter)
        
        scores_dict[col] = best_score
        n_states_dict[col] = best_n_states
        
        for _, row in df.iterrows():
            year = row['Año']
            province = row['Provincia']
            district = row['Distrito']
            initial_state = row[col]
            model = hmm.MultinomialHMM(n_components=best_n_states, n_iter=n_iter)
            model.startprob_ = np.array([1.0 / best_n_states] * best_n_states)
            model.transmat_ = best_model.transmat_
            model.emissionprob_ = np.eye(best_n_states)
            model.fit(X)
            
            simulated_states = forecast_hmm(model, n_weeks=20)
            decoded_states = categories[simulated_states]
            
            for week in range(2, 22):  # Semana 2 a Semana 21
                results.append({
                    'Año': year,
                    'Provincia': province,
                    'Distrito': district,
                    'Semana': week,
                    col: decoded_states[week - 2]
                })
    
    result_df = pd.DataFrame(results)
    
    return result_df, scores_dict, n_states_dict

# Ejemplo de uso
data = pd.DataFrame({
    'Año': [2020, 2021, 2022, 2023, 2024],
    'Provincia': ['Lima', 'Lima', 'Lima', 'Lima', 'Lima'],
    'Distrito': ['Miraflores', 'Miraflores', 'Miraflores', 'Miraflores', 'Miraflores'],
    'Estado1': ['Alta', 'Media', 'Baja', 'Media', 'Alta'],
    'Estado2': ['Baja', 'Alta', 'Media', 'Alta', 'Baja']
})

cat_columns = ['Estado1', 'Estado2']
result_df, scores_dict, n_states_dict = process_dataframe(data, cat_columns)
print(result_df)
print(scores_dict)
print(n_states_dict)
