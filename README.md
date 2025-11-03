# Data annotation app

This directory contains source code for simple data annotation app. It is a Streamlit application that allows users to annotate CTI reports relevance for a given user. Results of the annotation are 
stored in a JSON file that could be used as Ground Truth for evaluation whole Feat-3 solution.

### Running app

```bash
streamlit run app.py --server.port 8080
```