#!/usr/bin/env python
"""
Launcher script for the AI Study Buddy application.
Run this file to start the application.
"""
import streamlit.cli as stcli
import os
import sys

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "appy.py"]
    sys.exit(stcli.main())
