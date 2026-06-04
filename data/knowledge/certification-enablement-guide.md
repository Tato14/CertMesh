<!-- SYNTHETIC DOCUMENT — Northwind Health (fictional). For demonstration only.
     Real Microsoft exam codes are referenced for realism; skill lists, hours and
     thresholds are illustrative and are NOT official Microsoft exam content.
     Internal certs (CLIN-SAFE-*, GDPR-HC-2, TELEHEALTH-1, HL7-FHIR-1) are fictional. -->

# Northwind Health — Engineering & Clinical Certification Enablement Guide

This approved guide is the canonical learning source for Northwind Health's
workforce certification programme. The Learning Path Curator and the Assessment
Agent ground every recommendation and every practice question in the statements
below. All content is synthetic and for demonstration.

---

## AZ-900 — Microsoft Azure Fundamentals

AZ-900 (Microsoft Azure Fundamentals) validates foundational knowledge of cloud
concepts and core Azure services and is the recommended entry point before the
associate-level technical certifications. The recommended preparation is about
20 hours and the programme pass threshold is 70%.

### Skills and approved resources
- **Cloud concepts** — Cloud computing offers elasticity, where resources scale up or down on demand and you pay only for what you use. Approved resource: Module "Describe cloud computing".
- **Core Azure services** — A resource group is a logical container that holds related Azure resources and lets you manage them as a unit. Approved resource: Module "Describe Azure architecture and services".
- **Security and compliance** — Azure role-based access control (RBAC) grants the least-privilege permissions a user needs by assigning roles at a defined scope. Approved resource: Module "Describe Azure management and governance".
- **Pricing and SLAs** — A service-level agreement (SLA) is a formal commitment that states the expected availability of an Azure service. Approved resource: Module "Describe Azure pricing and SLAs".

### Exam-relevant facts
- Cloud elasticity means resources scale up or down on demand and you pay only for what you use.
- A resource group is a logical container that holds related Azure resources and lets you manage them together.
- Azure role-based access control (RBAC) grants least-privilege permissions by assigning roles at a defined scope.
- A service-level agreement (SLA) states the expected availability of an Azure service.

---

## AZ-204 — Developing Solutions for Microsoft Azure

AZ-204 (Developing Solutions for Microsoft Azure) validates a developer's ability
to build, deploy and maintain cloud applications and services on Azure. The
recommended prerequisite is AZ-900, the recommended preparation is about 60 hours,
and the programme pass threshold is 70%.

### Skills and approved resources
- **Azure App Service** — Azure App Service hosts web applications and APIs and supports deployment slots so a new version can be staged and swapped into production with zero downtime. Approved resource: Module "Create Azure App Service web apps".
- **Azure Functions** — Azure Functions runs event-driven code without managing servers, and a trigger defines how a function is invoked. Approved resource: Module "Implement Azure Functions".
- **Azure Storage** — Azure Blob Storage offers hot, cool and archive access tiers so you can match storage cost to how often data is read. Approved resource: Module "Develop solutions that use Azure Blob Storage".
- **Azure Cosmos DB** — Azure Cosmos DB offers multiple consistency levels, and choosing a weaker level such as session improves latency and availability. Approved resource: Module "Develop solutions that use Azure Cosmos DB".
- **Key Vault and managed identity** — An application should retrieve secrets from Azure Key Vault using a managed identity so that credentials are never stored in code. Approved resource: Module "Implement secure cloud solutions".
- **Container Apps** — Azure Container Apps runs containerised microservices and scales them automatically based on HTTP traffic or event load. Approved resource: Module "Implement containerized solutions".

### Exam-relevant facts
- Azure App Service deployment slots let a new version be staged and swapped into production with zero downtime.
- In Azure Functions, a trigger defines how a function is invoked.
- Azure Blob Storage provides hot, cool and archive access tiers to match cost to how often data is read.
- An application should retrieve secrets from Azure Key Vault using a managed identity so credentials are never stored in code.
- Azure Container Apps scales containerised microservices automatically based on HTTP traffic or event load.

---

## AZ-400 — Designing and Implementing Microsoft DevOps Solutions

AZ-400 (Designing and Implementing Microsoft DevOps Solutions) validates the
ability to combine people, process and technologies to deliver value continuously.
The recommended prerequisite is AZ-204, the recommended preparation is about 80
hours, and the programme pass threshold is 70%.

### Skills and approved resources
- **CI/CD pipelines** — A continuous integration pipeline builds and tests every code change automatically so integration problems are caught early. Approved resource: Module "Implement CI with Azure Pipelines".
- **Infrastructure as Code** — Infrastructure as Code defines environments declaratively so they can be provisioned reproducibly from version control. Approved resource: Module "Implement Infrastructure as Code with Bicep".
- **Release management** — A release approval gate pauses a deployment until a required check or human approval is satisfied. Approved resource: Module "Manage release cadence with deployment patterns".
- **Secure DevOps** — Secure DevOps scans dependencies and code for vulnerabilities as part of the pipeline rather than after release. Approved resource: Module "Implement security in the DevOps pipeline".
- **Observability and feedback** — Observability uses metrics, logs and traces to detect and diagnose problems in production. Approved resource: Module "Implement continuous feedback".

### Exam-relevant facts
- A continuous integration pipeline builds and tests every code change automatically so integration problems are caught early.
- Infrastructure as Code defines environments declaratively so they can be provisioned reproducibly from version control.
- A release approval gate pauses a deployment until a required check or human approval is satisfied.
- Secure DevOps scans dependencies and code for vulnerabilities as part of the pipeline rather than after release.
- Observability uses metrics, logs and traces to detect and diagnose problems in production.

---

## DP-203 — Data Engineering on Microsoft Azure

DP-203 (Data Engineering on Microsoft Azure) validates the ability to design and
implement data storage, processing and security on Azure. The recommended
prerequisite is AZ-900, the recommended preparation is about 70 hours, and the
programme pass threshold is 70%.

### Skills and approved resources
- **Data storage design** — A data lake stores raw data in open file formats so it can be processed by many engines without copying. Approved resource: Module "Design a data storage structure".
- **Batch and stream processing** — Batch processing handles large bounded datasets on a schedule, while stream processing handles unbounded events in near real time. Approved resource: Module "Ingest and transform data".
- **Azure Synapse Analytics** — Azure Synapse Analytics combines data warehousing and big-data analytics in a single workspace. Approved resource: Module "Work with Azure Synapse Analytics".
- **Data security and governance** — Column-level security restricts access to sensitive columns such as patient identifiers without hiding the whole table. Approved resource: Module "Secure a data platform".
- **Pipeline orchestration** — A data pipeline orchestrates activities such as copy, transform and validate, and can be triggered on a schedule or by an event. Approved resource: Module "Orchestrate data movement".

### Exam-relevant facts
- A data lake stores raw data in open file formats so it can be processed by many engines without copying.
- Batch processing handles large bounded datasets on a schedule, while stream processing handles unbounded events in near real time.
- Azure Synapse Analytics combines data warehousing and big-data analytics in a single workspace.
- Column-level security restricts access to sensitive columns such as patient identifiers without hiding the whole table.
- A data pipeline can be triggered on a schedule or by an event.

---

## HL7-FHIR-1 — Health Interoperability with FHIR (internal)

HL7-FHIR-1 (Health Interoperability with FHIR) is a Northwind Health internal
certification covering the FHIR standard for exchanging healthcare data. The
recommended prerequisite is AZ-900, the recommended preparation is about 35 hours,
and the programme pass threshold is 75%.

### Skills and approved resources
- **FHIR resources** — In FHIR, a resource is the smallest unit of exchange, and a Patient resource represents demographic and administrative data about an individual receiving care. Approved resource: Module "FHIR resources and the data model".
- **RESTful FHIR APIs** — A FHIR server exposes resources over a RESTful API where each resource type has a predictable endpoint. Approved resource: Module "Read and write data with the FHIR REST API".
- **Terminology and code systems** — FHIR uses code systems such as SNOMED CT and LOINC so that clinical concepts are represented consistently across systems. Approved resource: Module "Terminology and value sets in FHIR".
- **Interoperability standards** — Interoperability lets different healthcare systems exchange data and use it without ambiguity. Approved resource: Module "Standards-based interoperability".

### Exam-relevant facts
- In FHIR, a resource is the smallest unit of exchange, and a Patient resource represents demographic and administrative data about an individual.
- A FHIR server exposes resources over a RESTful API where each resource type has a predictable endpoint.
- FHIR uses code systems such as SNOMED CT and LOINC so clinical concepts are represented consistently across systems.
- Interoperability lets different healthcare systems exchange data and use it without ambiguity.

---

## CLIN-SAFE-1 — Clinical Safety Foundations (internal)

CLIN-SAFE-1 (Clinical Safety Foundations) is a Northwind Health internal
certification introducing clinical risk management for health IT systems. The
recommended preparation is about 25 hours and the programme pass threshold is 75%.
There is no prerequisite.

### Skills and approved resources
- **Clinical risk basics** — Clinical risk management identifies, analyses and controls hazards that a health IT system could introduce to patient safety. Approved resource: Module "Foundations of clinical risk".
- **Hazard logging** — A hazard log is the living record of every identified clinical hazard together with its risk rating and the controls applied. Approved resource: Module "Maintaining a hazard log".
- **Clinical safety case** — A clinical safety case is the structured argument and evidence that a system is acceptably safe for its intended use. Approved resource: Module "Building a clinical safety case".
- **Incident reporting** — A clinical safety incident must be reported promptly so that harm can be mitigated and the hazard log updated. Approved resource: Module "Clinical incident reporting".

### Exam-relevant facts
- Clinical risk management identifies, analyses and controls hazards that a health IT system could introduce to patient safety.
- A hazard log is the living record of every identified clinical hazard together with its risk rating and the controls applied.
- A clinical safety case is the structured argument and evidence that a system is acceptably safe for its intended use.
- A clinical safety incident must be reported promptly so that harm can be mitigated and the hazard log updated.

---

## CLIN-SAFE-2 — Clinical Safety Practitioner (internal)

CLIN-SAFE-2 (Clinical Safety Practitioner) is a Northwind Health internal
certification for practitioners who own clinical risk management for a system. The
recommended prerequisite is CLIN-SAFE-1, the recommended preparation is about 40
hours, and the programme pass threshold is 80%.

### Skills and approved resources
- **Clinical risk management plan** — A clinical risk management plan defines the activities, responsibilities and acceptance criteria for managing clinical risk across a system's lifecycle. Approved resource: Module "Authoring a clinical risk management plan".
- **Safety case authoring** — A safety case must be revisited whenever a significant change is made to the system, because the change can introduce new hazards. Approved resource: Module "Maintaining the safety case through change".
- **Hazard workshop facilitation** — A hazard identification workshop brings clinical and technical staff together to find hazards that neither group would find alone. Approved resource: Module "Facilitating hazard workshops".
- **Post-market surveillance** — Post-market surveillance monitors a deployed system for emerging hazards using incident reports and usage data. Approved resource: Module "Post-deployment clinical safety monitoring".

### Exam-relevant facts
- A clinical risk management plan defines the activities, responsibilities and acceptance criteria for managing clinical risk across a system's lifecycle.
- A safety case must be revisited whenever a significant change is made to the system, because the change can introduce new hazards.
- A hazard identification workshop brings clinical and technical staff together to find hazards that neither group would find alone.
- Post-market surveillance monitors a deployed system for emerging hazards using incident reports and usage data.

---

## TELEHEALTH-1 — Telehealth Systems Operations (internal)

TELEHEALTH-1 (Telehealth Systems Operations) is a Northwind Health internal
certification covering the safe operation of virtual-care services. The
recommended preparation is about 20 hours and the programme pass threshold is 70%.
There is no prerequisite.

### Skills and approved resources
- **Virtual consultation workflow** — A virtual consultation follows a defined workflow of pre-checks, identity verification, the consultation itself and documented follow-up. Approved resource: Module "Running a safe virtual consultation".
- **Device onboarding** — A patient device must be onboarded and tested before the first consultation so technical failure does not occur mid-appointment. Approved resource: Module "Onboarding patient devices".
- **Patient identity verification** — Patient identity must be verified at the start of every telehealth session using at least two approved identifiers. Approved resource: Module "Verifying patient identity remotely".
- **Telehealth incident handling** — If a telehealth session fails, the clinician must fall back to a pre-agreed alternative channel so care is not interrupted. Approved resource: Module "Handling telehealth incidents".

### Exam-relevant facts
- A virtual consultation follows a defined workflow of pre-checks, identity verification, the consultation itself and documented follow-up.
- A patient device must be onboarded and tested before the first consultation so technical failure does not occur mid-appointment.
- Patient identity must be verified at the start of every telehealth session using at least two approved identifiers.
- If a telehealth session fails, the clinician must fall back to a pre-agreed alternative channel so care is not interrupted.

---

## GDPR-HC-2 — Healthcare Data Protection Practitioner (internal)

GDPR-HC-2 (Healthcare Data Protection Practitioner) is a Northwind Health internal
certification covering data protection for health and care data. The recommended
preparation is about 30 hours and the programme pass threshold is 80%. There is no
prerequisite.

### Skills and approved resources
- **Lawful basis for health data** — Processing health data requires both a lawful basis and a separate condition for processing special category data. Approved resource: Module "Lawful basis and special category data".
- **DPIA for clinical systems** — A data protection impact assessment (DPIA) must be completed before deploying a system that processes health data at scale. Approved resource: Module "Conducting a DPIA".
- **Subject access requests** — A subject access request lets an individual obtain a copy of their personal data, and it must normally be answered within one month. Approved resource: Module "Handling subject access requests".
- **Breach handling** — A personal data breach that risks people's rights must be reported to the supervisory authority without undue delay, normally within 72 hours. Approved resource: Module "Responding to a data breach".
- **Special category data** — Health data is special category data and requires stronger safeguards than ordinary personal data. Approved resource: Module "Protecting special category data".

### Exam-relevant facts
- Processing health data requires both a lawful basis and a separate condition for processing special category data.
- A data protection impact assessment (DPIA) must be completed before deploying a system that processes health data at scale.
- A subject access request must normally be answered within one month.
- A personal data breach that risks people's rights must be reported to the supervisory authority within 72 hours.
- Health data is special category data and requires stronger safeguards than ordinary personal data.
