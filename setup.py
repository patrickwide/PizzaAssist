from setuptools import setup, find_packages

setup(
    name="ai_app",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'fastapi',
        'uvicorn',
        'langchain',
        'langchain-core',
        'ollama'
    ],
)
