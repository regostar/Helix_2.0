from setuptools import setup, find_packages

setup(
    name="helix-backend",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'flask',
        'flask-socketio',
        'flask-cors',
        'flask-sqlalchemy',
        'langchain',
        'langchain-openai',
        'python-dotenv',
        'eventlet',
        'pandas',
        'psycopg2-binary'
    ]
) 