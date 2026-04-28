from setuptools import setup, find_packages

setup(
    name="seo-brief",
    version="0.1.0",
    py_modules=["brief"],
    packages=find_packages(),
    install_requires=[
        "groq>=0.9.0",
        "google-genai>=1.0.0",
        "langfuse>=2.0.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "brief=brief:cli",
        ],
    },
    python_requires=">=3.9",
)
