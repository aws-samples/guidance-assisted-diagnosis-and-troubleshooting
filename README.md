# Guidance For Assisted Diagnosis and Troubleshooting on AWS

This repository contains guidance for implementing a generative AI powered assisted diagnosis and troubleshooting solution using Amazon Bedrock. The guidance is designed for Automotive & Manufacturing businesses looking to improve shop floor productivity with faster diagnosis and issue resolution.

## Overview

Unlocking valuable insights hidden within industrial data can significantly enhance efficiency, reduce costs, and improve overall productivity across various sectors. One of the most critical challenges in industrial environments is managing and extracting value from unstructured data, such as equipment maintenance records, sensor readings, and Standard Operating Procedures (SOPs).  Generating actionable insights from this complex data is essential for maintaining operational excellence but remains a significant challenge.

The **Assisted Diagnosis and Troubleshooting Guidance**, powered by generative AI, offers an innovative solution to addressing these challenges.Shop floor operators and operational managers can use natural language interactions to quickly diagnose and resolve production issues, submit work orders, and access internal documentation. Through AI-driven recommendations and advanced data integration, this solution helps operators identify problems more efficiently, reducing downtime and improving overall equipment effectiveness (OEE). Leveraging AWS Generative AI services like Amazon Bedrock and Amazon Q, the guidance combines techniques such as text generation, chat experiences, entity extraction, and retrieval-augmented generation (RAG) to provide operators with personalized, data-driven recommendations that enable swift root cause identification and effective resolution. 

This guidance builds on AWS Industrial IoT services to create a centralized hub for operational data, integrating diverse sources such as sensors, PLCs, SCADA, ERP, and MES systems. The operational data is enriched with historical context and fully contextualized within AWS IoT Services like IoT SiteWise and IoT TwinMaker, where it can be used to build a digital twin of the production systems. The digital twin, combined with a knowledge graph of the production process, provides real-time insights into industrial assets and their operational states. Generative AI is then employed to extract valuable insights from various data types, including operational, contextual, and unstructured data. With AWS IoT services, operators gain real-time visibility into equipment performance, while generative AI services like Amazon Bedrock and Amazon Q provide foundational models to generate detailed diagnostics, submit work orders, and assist with troubleshooting.

Key features of the guidance include:
- **User Interactions**: The system continuously monitors sensor data and production events, providing operators with real-time insight
- **Intent and Entity Extraction**: The chat interface uses natural language processing (NLP) techniques to extract the user's intent and relevant entities, such as events, equipment, sensor data related to specific equipment.
- **Knowledge Base and Retrieval-Augmented Generation (RAG)**: The extracted intent and entities are used to query corporate data in the knowledge base which contains a comprehensive dataset of SOPs, equipment manuals, and related information. The system also queries OT data from data historians, maintenance systems, and contextualized data from IoT Sitewise. The RAG model generates diagnoses and recommendations by combining retrieved knowledge with enterprise asset models, historical data, and real-time sensor inputs.
- **Text Generation**: Language models generate textual responses, providing users with detailed step-by-step troubleshooting diagnostics, repair instructions, and best practices to help operators find relevant solutions effortlessly.
- **Gen AI-Powered Issue Resolution**:  The AI assistant customizes resolution suggestions based on the context of the identified root cause, ensuring recommendations are relevant, actionable, and compliant with equipment manuals and company SOPs. It can also initiate work orders for maintenance or repair actions based on the detected issues.
- **Seamless Integration**: The assistant integrates into the operator's workflow, allowing them to verify root cause diagnoses, access internal documentation, and submit work orders directly from the application.



## Implementation guides

[Assisted Diagnosis and Troubleshooting on AWS with Amazon Bedrock](/bedrock/README.md)

[Assisted Diagnosis and Troubleshooting on AWS with Amazon Q](/amazonQ/README.md)

