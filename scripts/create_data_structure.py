#!/usr/bin/env python3

import os
from pathlib import Path
import logging
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

def create_directories(directories):
    logger.info("Creating base directory structure...")
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True)
            logger.info(f"Created directory: {directory}")
        else:
            logger.info(f"Directory already exists: {directory}")

def create_files(file_paths):
    logger.info("Creating placeholder files in data/documents...")
    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            path.touch()
            logger.info(f"Created file: {file_path}")
        else:
            logger.info(f"File already exists: {file_path}")
