#!/bin/bash
echo "Instalando dependencias..."
pip install -r requirements.txt --quiet
echo "Iniciando Generacion de EPW..."
streamlit run app_solar.py
