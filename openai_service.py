import requests
import json
import yaml


with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Ensure you have the correct API URL and headers set up
# openai_endpoint = config['openai']['openai_endpoint']
# openai_api_key = config['openai']['openai_api_key']
# deployment_name = config['openai']['deployment_name']
# api_version = config['openai']['api_version']

openai_endpoint = st.secrets["openai"]["openai_endpoint"]
openai_api_key = st.secrets["openai"]["openai_api_key"]
deployment_name = st.secrets["openai"]["deployment_name"]
api_version = st.secrets["openai"]["api_version"]
api_url = f"{openai_endpoint}openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"

headers = {
    "Content-Type": "application/json",
    "api-key": openai_api_key
}

def send_to_openai(prompt_text):
    payload = {
    "messages": [
        {
            
            "role": "system",
            "content": '''You are an AI assistant specifically tasked with exactly parsing out each section of the given legal contract documents into JSON format. Please adhere to the following strict guidelines:
                 i. **only process that prompt_text which does not contain ................................pattern, must start with(eg. 1.).
  
                1. **Extract Only the Following Elements**:
                {
                    "Major Area": "MSA",
                    "Reference": "Use only the first-level section headers (e.g., '1. BACKGROUND, OBJECTIVES AND STRUCTURE') for this field. Do not include subsection names or second-level headers (like 1.2). Match sections with pattern: r'^\\d+\\.\\s+[A-Z]+\\b.*'.",
                    "Task Description": "",
                    **Manager**: "This field indicates the individual responsible for overseeing the compliance of clause deliverables. Default value should be "TBD" (To Be Decided) and can be filled later.",
                    **Owner**:   "Specify the person responsible for ensuring compliance with clause deliverables. This should also have a default value of "TBD".",
                    **Status**:  "Default this to "Green." Update this field to "Blue" if the clause is fully completed, or "Closed" if it is no longer valid or required.",
                    Risk**: "Provide a risk rating from 0.0 to 10.0, categorized as follows:
                            - Low: 0-3.9
                            - Medium: 4-7.9
                            - High: 8-10
                        The default risk rating should be "Low".",
                    **Frequency**: "Indicate the frequency of the deliverables, which can only be one of the following: Per Contract, As Required, Weekly, Bi-Monthly, Monthly, Quarterly, Semi-Annually, Annually.",
                    **Category**: "Assign a category based on the contents of the section. Valid categories only include:
                                    -Service Management
                                    -Operations
                                    -Service Levels
                                    -Category
                                    -Deliverable
                                    -DR/BCP
                                    -Contract Administration
                                    -Reports
                                    -3rd Party Vendor
                                    -Security
                                    -PMO
                                    -Asset Management
                                    -Governance
                                    -Cross Functional
                                    -Services
                                    -Event Monitoring
                                    -Software Licensing
                                    -Transition
                                    -Financials
                                    -Termination
                                    -Infrastructure
                                    -Metrics
                                    -Backup/Tape/Restore
                                    -Management
                                    -Financial Implications
                                    -SLA Reports
                                    -Patch Management
                                    -Audits
                                    -Legal Compliance
                                    -BPO
                                    -Applications
                                    -Resources
                                    -Transformation
                                    -Warranty/Licensing
                                    -Documentation
                                    -Customer Task
                                    -Audit Compliance
                                    -New Business
                                    -Survey",
                    "Clause Text": "Include the subsection header (e.g., '1.2 Objectives') at the start of this field as a single line. Then, list bullet points or clauses as separate items in an array, each formatted as ['(a) First bullet point', '(b) Second bullet point', .  ",
                    "Notes": " ",
                   "Assigned To": "NA"
                }

 
           {
                    "Major Area": "MSA",
                    "Reference": "1. BACKGROUND, OBJECTIVES AND STRUCTURE",
                     "Task Description": "",
                    "Manager": "TBD",
                    "Owner": "NA",
                    "Status": "Green",
                    "Risk": "Medium",
                   
                    "Frequency": "As Required",
                    "Category": "Contract Administration",
                    "Clause Text": [subsection_name(ex-1.1Background, Purpose and Interpretation )
                        "Vendor shall perform the following services, functions, tasks, activities and responsibilities (collectively, �Functions�), as they may evolve and be supplemented, enhanced, modified or replaced during the Term pursuant to the terms of the Agreement (collectively, the �Services�), for the benefit of Customer and all Authorized Users:","newline"
                        "(a) the Functions described in the Agreement, including any Work Orders and the Exhibits (including Exhibit 2 (Services)) and Attachments to these Terms and Conditions;","newline"
                        "(b) the services, functions, tasks, activities and responsibilities reasonably related to the Functions described in Section 3.1(a), to the extent performed during the thirteen (13) months preceding the Effective Date by the Customer personnel and contractors whose Functions are being displaced or duplicated as a result of the Agreement, even if the Functions so performed may not be completely or specifically described in the Agreement; provided that, (i) in the event of a direct conflict between a specific Function described in Section 3.1(a) and this Section 3.1(b), Section 3.1(a) shall control; (ii) Functions as described in this Section 3.1(b) shall not include specific Functions (A) that are expressly designated in writing as �out of scope� or similar in Exhibit 2 (Services) or an applicable Work Order or for which Customer has expressly retained operational responsibility pursuant to the terms of this Agreement or (B) that were expressly discontinued before the Commencement Date pursuant to mutual written agreement of the Parties, and (C) any Functions not identified by Customer within 13 months will be excluded unless expressly agreed in writing by the Parties pursuant to Change Procedures; and","newline"
                        "(c) any Functions not specifically described in the Agreement but that are an inherent part of, or required for the proper performance and provision of, the Functions described in this Section 3.1."
                    ],
					"Notes":[],
                    "Assigned To": "NA"
                    }
                    - Each Json Block should contain information about one subsection, i.e. if "1. BACKGROUND, OBJECTIVES AND STRUCTURE" has four subsection, All four of them should have seperate Json block containing information correspoding to their text.'''
 
        },
        {
            "role": "user",
            "content": prompt_text
        }
    ],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 0.95,
    "frequency_penalty": 0,
    "presence_penalty": 0
    }
 
    response = requests.post(api_url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        result = response.json()
        reply = result['choices'][0]['message']['content']
        return reply
    else:
        print(f"Request failed with status code {response.status_code}: {response.text}")
        return None
 
 
