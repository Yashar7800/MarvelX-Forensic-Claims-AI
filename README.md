# MarvelX Forensic Claims AI

**An Intelligent Multi-Agent System for Automated Insurance Claim Verification.**

# Project Overview

`In the traditional insurance world, verifying claims is a slow, manual process prone to human error. MarvelX Forensic Claims AI leverages a collaborative multi-agent architecture to instantly analyze proof of loss, cross-reference documentation, and detect discrepancies (like date mismatches or invalid OCR data) using a forensic-first approach.`

# Key Features

* Multi-Agent Logic: Orchestrated by LangGraph, featuring a Gateman (initial screening) and an Auditor (final verification).

* Forensic OCR: Integrated EasyOCR to extract and validate text from medical notes and receipts.

* Automated Kill-Switches: Instant rejection logic for redacted documents or invalid photographic evidence.

* Modern UI: A sleek, glassmorphism-inspired web interface built with Flask.

* Transparent Reasoning: Detailed JSON-based decision logs explaining the why behind every verdict.