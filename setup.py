from setuptools import setup, find_packages

def load_requirements():
    with open("requirements.txt") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="ai_app",
    version="0.1",
    packages=find_packages(),
    install_requires=load_requirements(),
)
