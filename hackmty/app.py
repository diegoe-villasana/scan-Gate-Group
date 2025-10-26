from flask import Flask, render_template
import pandas as pd
import joblib
from tensorflow import keras

app = Flask(__name__)

MODEL_PATH = "model/prediccion_consumo_REAL_ADV_CORR_v1.keras"
PREPROC_PATH = "model/preprocesador_consumo_REAL_ADV_CORR_v1.joblib"

model = keras.models.load_model(MODEL_PATH)
preprocessor = joblib.load(PREPROC_PATH)

try:
    df_original = pd.read_csv("data/[HackMTY2025]_ConsumptionPrediction_Dataset_v1.csv")
except FileNotFoundError:
    print("ADVERTENCIA: No se encontró el .csv, intentando cargar el .xlsx...")
    df_original = pd.read_excel("data/[HackMTY2025]_ConsumptionPrediction_Dataset_v1.xlsx")

@app.route("/")
def home():
    df_analisis = df_original.copy()
    df_analisis['Product_Category'] = df_analisis['Product_ID'].str.slice(0,3)
    
    features = ['Origin', 'Flight_Type', 'Service_Type', 'Passenger_Count', 'Product_Category']
    X = preprocessor.transform(df_analisis[features])

    predicciones = model.predict(X).flatten()
    df_analisis['Predicted_Consumption'] = predicciones
    df_analisis['Predicted_Waste'] = df_analisis['Standard_Specification_Qty'] - df_analisis['Predicted_Consumption']
    df_analisis['Predicted_Waste'] = df_analisis['Predicted_Waste'].clip(lower=0)
    df_analisis['Waste_Percentage'] = (df_analisis['Predicted_Waste'] / df_analisis['Standard_Specification_Qty'] * 100).round(2)
    
    report = df_analisis[['Product_Name', 'Predicted_Waste', 'Waste_Percentage']].head(10).to_dict(orient='records')
    
    return render_template("index.html", report=report)

@app.route("/scanner")
def scanner_page():
    return render_template("scanner.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000) 

# --- Esta es la parte que usaremos para DEPLOY (la dejamos comentada) ---
# if __name__ == "__main__":
#     import os
#     port = int(os.environ.get("PORT", 10000))
#     app.run(host="0.0.0.0", port=port)

