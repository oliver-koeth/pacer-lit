# Pacer Streamlit Project
This repo provides a notebook to predict the pace for a given gps track based on a
base pace plus the uphill/downhill "penalties" from the base pace based on the
elevation per 100m. The pace prediction is based on a regression model which
is trained with a "reference run". The closer the reference run is to the 
predicted run (duration, elevation, technicality) the better the prediction.

This repo includes two of my longer reference runs (Wank and Osterfeldkopf) plus
two races (Karwendelmarsch and Innsbruck Alpine Trail Festival) and
provides a prediction for the Zugspitz Supertrail XL course. Of course you can replace 
the GPX files in `./data` with your own files and re-run the notebook.

## TODO
[x] RACRPACR Project
[x] Complete Data
[x] Write Introduction
[ ] Reset Function
[ ] Library Files
[ ] Scale Results
[ ] Demo Video
[ ] CRUD Splits


## Run locally in conda
When running for the first time, create a respective conda environment. In case
of doubt whether a conda environment exists, you can list all environments
(the environment for this project is called `pacer-lit-env`, the environment file 
uses the extension `.local` so that Stremalit.io cloud does not get confused.):
```
conda env list
conda env create -f environment.yml.local
conda activate pacer-lit-env
pip install -r requirements.txt
```

Now run:
```
streamlit run pacer_lit.py
```

To eventually remove the environment run:
```
conda deactivate
conda remove --name pacer-lit-env --all
```

## Deploy on Streamlit Cloud


