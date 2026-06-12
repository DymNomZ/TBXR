# **Project Proposal** 

## **Team Information**

Project Title: TB-XR

Project Short Description: A collaborative, AI-integrated teleradiology platform for Pulmonary Tuberculosis screening, featuring multi-user workflows, radiologist annotation, and longitudinal patient monitoring.

Team Code: 2526-sem2-cs342-06

Members:

1\. Borgonia, John Dymier  
2\. Emia, Seth Nathaniel  
3\. Enario, Lance Joseph Lorenz  
4\. Epan, Raimar Shaun  
5\. Tolentino, Brent Micheal

## **PART 1: Introduction**

	Tuberculosis remains one of the leading infectious diseases worldwide, particularly in low, and middle income countries where healthcare resources are limited and early diagnosis is often delayed. Delays in TB diagnosis and treatment contribute significantly to continued spreading of the disease. Research has shown that patients in high-burden countries often experience prolonged delays due to limited access to healthcare facilities, lack of awareness, financial barriers, and complex healthcare systems [(Teo et al. 2021\)](https://www.zotero.org/google-docs/?AIfwOn). These challenges highlight the need for faster and more accessible diagnostic methods that can support early detection and treatment initiation.

	Chest X-ray imaging is one of the most widely used screening tools for pulmonary tuberculosis, particularly in large-scale screening programs. However, the accurate interpretation of chest X-ray images requires trained radiologists and medical experts. In many healthcare systems, especially in developing countries, the number of qualified radiologists is limited, creating a bottleneck in the diagnostic process. This shortage can result in delayed image interpretation and inconsistent diagnostic decisions, which may negatively affect patient care. Studies have emphasized that the lack of skilled medical professionals and limited healthcare infrastructure significantly contribute to diagnostic challenges in TB screening programs [(Nampewo, Ariana, and Vijayan 2024\)](https://www.zotero.org/google-docs/?bnqBGQ).

 The current TB screening workflow suffers from isolated data and communication bottlenecks between radiologic technologists who capture the images and the limited number of specialists who interpret them. When diagnostic processes lack a collaborative, transactional platform, patients experience delayed treatment, and clinics lose the ability to track disease progression over time. Furthermore, inefficient screening systems can lead to missed cases or unnecessary confirmatory testing, increasing healthcare costs and resource utilization. [(Teo et al. 2021\)](https://www.zotero.org/google-docs/?2k5gjK). Evidence from recent studies indicates that AI-assisted chest X-ray screening systems can improve detection efficiency and support clinical workflows, particularly in settings where medical expertise and diagnostic resources are limited [(Hansun et al. 2023\)](https://www.zotero.org/google-docs/?ymrmBO).

Based on the challenges identified in the background, the primary problem addressed in this project is the difficulty of achieving fast, accurate, and accessible tuberculosis screening using chest X-ray images, particularly in healthcare environments with limited radiological expertise and resources [(Hansun et al. 2023\)](https://www.zotero.org/google-docs/?7vd6xa). 

Many studies focus on algorithm development and model evaluation in experimental environments rather than on building complete software systems that healthcare workers can actually use in practice under experimental conditions rather than the development of accessible and practical software systems that can support real-world TB screening workflows. Systematic reviews note that despite promising results, only a limited number of AI models have been translated into operational tools used in clinical practice [(Hansun et al. 2023\)](https://www.zotero.org/google-docs/?nNJNpS)

## **PART 2: Objectives**

1. **Automate the ingestion, standardization, and secure storage of patient X-ray data.**  
   1. Implement a secure upload module for Radiologic Technologists to input digital X-ray images (e.g., DICOM, JPEG) alongside patient metadata.  
   2. Standardize image formats automatically (resizing, contrast enhancement) and link them to unique patient profiles in a centralized database to establish a transaction history.  
2. **Facilitate collaborative diagnostic workflows through an interactive annotation system.**  
   1. Develop a dedicated interface for Radiologists to remotely access queued X-rays.  
   2. Implement interactive bounding-box and text-annotation tools, allowing specialists to manually highlight anomalies, correct AI findings, and submit official diagnostic reviews.  
3. **Provide AI-assisted risk analysis and longitudinal disease monitoring.**  
   1. Integrate a lightweight Convolutional Neural Network (CNN) to automatically generate baseline TB probability scores upon image upload.  
   2. Develop a comparative logic module that retrieves a patient’s historical X-ray records and calculates disease progression or regression over time, presenting this data to the reviewing radiologist.  
4. **Streamline clinical decision-making via comprehensive reporting dashboards.**  
1. Construct role-specific dashboards (Technician, Radiologist, Doctor) that track the real-time status of X-ray transactions (e.g., "Pending Review," "Annotated," "Completed").  
2. Generate downloadable, comprehensive patient reports that synthesize the AI risk score, the radiologist’s manual annotations, and the longitudinal progression data for the attending physician.

**Research Questions**

* How can a deep learning model be designed and validated for reliable tuberculosis detection using chest X-ray images?  
* How can an AI-based TB detection model be designed to operate effectively in environments with limited computing resources?  
* How can AI-assisted screening tools help reduce diagnostic delays in TB detection?  
* How can AI-based TB detection systems be adapted to support TB screening programs in the Philippine healthcare context?  
* How can an AI screening system be integrated into clinical workflows to assist early TB detection?

## **PART 3: Methods**

The proposed solution is a lightweight tuberculosis detection system that analyzes chest X-ray images and makes diagnostic predictions with minimal processing power. The system combines an image preprocessing module to standardize input, a user-friendly interface for results visualization, and a pre-trained AI model for TB detection. It solves the identified issue by making it possible for medical professionals, especially in settings with limited resources, to promptly screen patients for tuberculosis (TB) without depending on sophisticated computing power or a large number of radiologists. Clinicians, radiology technicians, and primary care physicians in low-resource clinics or mobile health units are the target users; patients who receive quicker and easier access to TB screening are the secondary beneficiaries.

The project will follow the Agile Development Methodology, structured into one-week iterative sprints to ensure that design decisions are responsive to testing outcomes. Development is organized into four primary phases corresponding to the system’s core modules:

**Sprint 1:** Data Ingestion & Patient Profiling: Development of the tech-facing upload portal, image normalization pipeline, and the relational database schema linking images to patient IDs.

**Sprint 2:** Radiologist Annotation Module: Implementation of the remote viewing dashboard and interactive image annotation tools (bounding boxes, tagging) for specialists.

**Sprint 3:** AI Integration & Longitudinal Comparison: Connecting the pre-trained lightweight CNN to generate initial risk scores, and building the logic to compare current scans with historical patient data.

**Sprint 4:** Role-Based Dashboards & Reporting: Finalizing the UI/UX for the Doctor's view, aggregating AI scores and human annotations into exportable clinical reports.

System validation will be conducted across three primary dimensions to demonstrate effectiveness and reliability:

1. **Diagnostic Accuracy:** The model’s performance will be validated against standard clinical metrics, specifically aiming for ≥90% Sensitivity (Recall) and \>70% Specificity to align with WHO triage guidelines.  
2. **Computational Inference:** Performance will be quantified by measuring prediction latency 5 seconds and system resource consumption (RAM and CPU usage) on a baseline low-end device (e.g. Intel Core i3, 4GB RAM).  
3. **System Usability:** User acceptance will be evaluated through structured testing with a target group of healthcare workers. Feedback will be measured using the System Usability Scale (SUS) to verify that the interface seamlessly integrates into the fast-paced workflows of rural clinics.  
   

## **PART 4: Expected System**

The anticipated software system is a collaborative, AI-integrated teleradiology platform designed to assist Radiologic Technologists, remote Radiologists, and attending Physicians in the rapid screening and continuous monitoring of Pulmonary Tuberculosis. The Minimum Viable Product (MVP) will include the following core functionalities:

1. **Multi-role Authentication and Access Control**  
   Secure login portals tailored to three specific user roles:  
   * **Radiologic Technologist:** Permissions restricted to uploading images and creating/updating patient records.  
   * **Radiologist:** Permissions to access the global queue of pending X-rays, utilize annotation tools, and submit official findings.  
   * **Attending Physician:** Permissions to view finalized, aggregated reports and historical patient data to make clinical decisions.

2. **Image Upload and Patient History Linking**

   * Accepts standard digital image formats (JPEG, PNG, DICOM-converted images) uploaded by technicians.  
   * Automatically normalizes image quality (contrast enhancement, resizing) for optimal AI analysis.  
   * Links every uploaded X-ray to a unique, searchable Patient Profile within a centralized database (specific to each hospital), maintaining a continuous transaction history.

3. **Interactive Radiologist Annotation Toolkit**

   * Simple web or desktop interface for uploading X-ray images, viewing results, and receiving system-generated recommendations.  
   * Dashboard for monitoring screened cases and flagged results.

4. **AI-based Baseline TB Risk Prediction**

   * Utilizes a lightweight Convolutional Neural Network (CNN) to automatically analyze the X-ray immediately upon upload.  
   * Generates a preliminary, quantitative probability score (e.g., "85% likelihood of TB") and a visual heatmap highlighting the areas the AI considers abnormal.  
   * Acts as a first-pass screening tool to prioritize highly suspicious cases in the radiologist's queue.

5. **Longitudinal X-ray Comparison (Disease Progression Tracking)**

   * Automatically retrieves a patient’s historical X-ray records and previous AI risk scores when a new scan is uploaded.  
   * Displays the current and past X-rays side-by-side within the radiologist's and physician's dashboards.  
   * Highlights changes in the AI risk score over time to assist in monitoring treatment efficacy or disease progression.

6. **Transactional Status Tracking Dashboard & Reporting**

   * Features a dynamic tracking system that updates the status of an X-ray transaction in real-time (e.g., "Awaiting AI Analysis" \-\> "Pending Radiologist Review" \-\> "Completed & Verified").  
   * Generates comprehensive, exportable clinical reports (PDF format) that synthesize the AI's risk score, the radiologist's manual annotations, and the patient's longitudinal history for the attending physician.

The high-level workflow demonstrates how users interact with the system and how information flows between components:

1. **Input**

   * A Radiologic Technologist captures a chest X-ray and logs into the system.  
   * The technician creates or retrieves a Patient Profile and uploads the digital X-ray image.  
   * The system preprocesses the image, assigns a unique Transaction ID, and links it to the patient's historical records.

2. **Processing**

   * Human-in-the-Loop Review: A remote Radiologist logs into their dashboard, selects a pending scan from the queue, and views both the raw image and the AI’s heatmap.  
   * Annotation: The radiologist uses the interactive toolkit to draw bounding boxes over abnormalities, compares the current scan against the patient's past X-rays, and submits their final, verified clinical notes. The transaction status updates to "Completed."  
   * AI Analysis: The lightweight CNN model immediately analyzes the image, logs a preliminary risk score, generates a heatmap, and flags high-risk cases for priority review.

3. **Output**

   * An Attending Physician accesses the patient’s profile via their dashboard.  
   * The system displays the final diagnostic package: the original image, the AI risk score, the radiologist's manual annotations, and a longitudinal comparison of past scans.  
   * The physician downloads a standardized, consolidated PDF report to finalize clinical decisions and initiate or adjust the patient's treatment plan.

## **PART 5: Discussion**

The scope of the system is focused on providing a functional, lightweight tuberculosis detection software capable of processing chest X-ray images and generating diagnostic predictions. The system includes modules for image upload, preprocessing, AI-based prediction using a pre-trained lightweight model, and visualization of results through a user-friendly interface. The operational coverage is designed for low-end devices, such as entry-level laptops or mobile phones, making the software suitable for use in resource-limited healthcare environments. The MVP will demonstrate the end-to-end workflow, allowing users to screen for TB efficiently while maintaining minimal computational requirements.

The project is subject to several limitations. First, the system’s performance depends on the availability and quality of chest X-ray data; the model may not generalize well to images with unusual orientations, artifacts, or rare comorbidities. Second, computational limitations of low-end devices may restrict real-time performance, particularly when processing large batches of images. Connectivity constraints in remote areas may also affect software updates or integration with cloud-based analytics. Finally, time restrictions for developing an MVP within a single semester mean that advanced features such as full dataset training, multi-class lung disease detection will not be implemented initially.

The expected contribution of the system lies in its ability to bridge the gap between AI research and practical deployment in low-resource settings. By providing a lightweight, efficient, and user-friendly TB detection tool, the system can support healthcare providers who lack access to high-end computational resources or expert radiologists. It introduces the capability for rapid, on-site TB screening, potentially improving early diagnosis and patient management. Additionally, the project addresses a clear research and technological gap in deploying AI models optimized for low-end devices, demonstrating how software engineering practices can make AI solutions more accessible and operational in real-world healthcare environments.

## **PART 6: Traceability Matrix**

| RRL Finding / Theme | Identified Gap | Research Question | Proposed Feature / Design Decision |
| ----- | ----- | ----- | ----- |
| Studies show that deep learning models can detect tuberculosis from chest X-ray images with high accuracy (often above 90%), demonstrating strong potential for automated screening. | Many studies are validated only on curated datasets and lack implementation in real-world clinical environments, particularly in primary healthcare facilities. | How can a deep learning model be designed and validated for reliable tuberculosis detection using chest X-ray images? | Develop a CNN-based TB detection model trained on publicly available datasets and validated using standard metrics (accuracy, sensitivity, specificity). |
| AI-based TB detection systems can achieve high accuracy but often require significant computational resources. Studies highlight infrastructure limitations in rural healthcare environments and the need for deployable AI solutions in low-resource settings. | Many AI models are computationally intensive and may not run efficiently in resource-constrained healthcare facilities. | How can an AI-based TB detection model be designed to operate effectively in environments with limited computing resources? | Develop a lightweight deep learning model optimized for efficient inference on standard hardware used in healthcare facilities. |
| The TB diagnostic workflow still contains major gaps, including delayed diagnosis, limited access to diagnostic tools, and inefficiencies in screening processes. | Current diagnostic processes can be slow and require multiple steps, delaying treatment initiation. | How can AI-assisted screening tools help reduce diagnostic delays in TB detection? | Implement an automated screening system capable of producing rapid preliminary results immediately after image upload. |
| AI-assisted TB detection has shown practical benefits in the Philippines, including improved screening efficiency and faster result turnaround.  | There is limited localized research exploring how AI-based TB detection tools can be adapted for Philippine healthcare environments. | How can AI-based TB detection systems be adapted to support TB screening programs in the Philippine healthcare context? | Develop a lightweight AI screening platform that can operate in low-resource healthcare environments and support early TB detection. |
| Real-world screening studies show that AI-based TB detection tools can significantly increase case detection and reduce radiologist workload.  | Integration of AI screening tools into routine healthcare workflows remains limited. | How can an AI screening system be integrated into clinical workflows to assist early TB detection? | Implement a workflow where the AI system acts as a triage tool, flagging high-risk cases for further diagnostic testing. |

## **PART 7: References**

[Hansun, Seng, Ahmadreza Argha, Siaw-Teng Liaw, Branko G. Celler, and Guy B. Marks. 2023\. “Machine and Deep Learning for Tuberculosis Detection on Chest X-Rays: Systematic Literature Review.” *Journal of Medical Internet Research* 25:e43154. doi:10.2196/43154.](https://www.zotero.org/google-docs/?iEE1Su) 

[Nampewo, Irene, Proochista Ariana, and Shibu Vijayan. 2024\. “Benefits of Artificial Intelligence versus Human-Reader in Chest X-Ray Screening for Tuberculosis in the Philippines.” *International Journal of Health Sciences and Research* 14(2):277–87. doi:10.52403/ijhsr.20240237.](https://www.zotero.org/google-docs/?iEE1Su) 

[Teo, Alvin Kuo Jing, Shweta R. Singh, Kiesha Prem, Li Yang Hsu, and Siyan Yi. 2021\. “Duration and Determinants of Delayed Tuberculosis Diagnosis and Treatment in High-Burden Countries: A Mixed-Methods Systematic Review and Meta-Analysis.” *Respiratory Research* 22(1). doi:10.1186/s12931-021-01841-6.](https://www.zotero.org/google-docs/?iEE1Su) 