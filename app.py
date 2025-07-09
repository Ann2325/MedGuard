from flask import Flask, render_template, request, jsonify, redirect, url_for
import pandas as pd
import ollama

app = Flask(__name__)

# Load the interaction dataset
try:
    interaction_df = pd.read_csv('db_drug_interactions.csv')    
    interaction_df['Drug 1'] = interaction_df['Drug 1'].str.lower()
    interaction_df['Drug 2'] = interaction_df['Drug 2'].str.lower()
except Exception as e:
    print(f"Error loading interaction dataset: {e}")
    interaction_df = None

# Load the drug details dataset
try:
    drug_details_df = pd.read_csv('drugs.csv')
    drug_details_df['drugName'] = drug_details_df['drugName'].str.lower()
except Exception as e:
    print(f"Error loading drug details dataset: {e}")
    drug_details_df = None

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/interaction-checker')
def interaction_checker():
    # Get patient details from query parameters if they exist
    patient_age = request.args.get('age', '')
    patient_conditions = request.args.get('conditions', '')
    medications = request.args.getlist('medications')
    
    # Initialize variables for interaction check
    interaction_description = None
    drug1_info = []
    drug2_info = []
    error_message = None
    interaction_details = None
    
    # If we have medications, automatically check interaction for the first two
    if medications and len(medications) >= 2 and interaction_df is not None and drug_details_df is not None:
        drug1 = medications[0].strip().lower()
        drug2 = medications[1].strip().lower()
        
        # Check if drugs exist in drug_details_df
        drug1_exists = not drug_details_df[drug_details_df['drugName'] == drug1].empty
        drug2_exists = not drug_details_df[drug_details_df['drugName'] == drug2].empty
        
        # Search for interaction
        interaction = interaction_df[((interaction_df['Drug 1'] == drug1) & (interaction_df['Drug 2'] == drug2)) | 
                                   ((interaction_df['Drug 1'] == drug2) & (interaction_df['Drug 2'] == drug1))]
        
        # Get drug details if they exist
        if drug1_exists:
            drug1_info = drug_details_df[drug_details_df['drugName'] == drug1].to_dict(orient='records')
        if drug2_exists:
            drug2_info = drug_details_df[drug_details_df['drugName'] == drug2].to_dict(orient='records')
        
        # Handle different scenarios
        if not drug1_exists and not drug2_exists:
            error_message = f"Neither '{drug1}' nor '{drug2}' were found in our database."
        elif not drug1_exists:
            error_message = f"'{drug1}' was not found in our database."
        elif not drug2_exists:
            error_message = f"'{drug2}' was not found in our database."
        elif interaction.empty:
            interaction_description = f"No known interactions found between {drug1} and {drug2}."
        else:
            interaction_description = interaction.iloc[0]['Interaction Description']
            interaction_details = {
                'drug1': drug1,
                'drug2': drug2,
                'description': interaction.iloc[0]['Interaction Description'],
                'severity': 'Moderate',  # You can add severity levels to your database if needed
                'recommendation': 'Consult your healthcare provider before taking these medications together.'
            }
    
    return render_template('interaction_checker.html',
                         patient_age=patient_age,
                         patient_conditions=patient_conditions,
                         patient_medications=medications,
                         interaction_description=interaction_description,
                         interaction_details=interaction_details,
                         drug1_info=drug1_info,
                         drug2_info=drug2_info,
                         error_message=error_message)

@app.route('/check-interaction', methods=['POST'])
def check_interaction():
    interaction_description = None
    drug1_info = []
    drug2_info = []
    error_message = None
    interaction_details = None
    
    if interaction_df is not None and drug_details_df is not None:
        drug1 = request.form['drug1'].strip().lower()
        drug2 = request.form['drug2'].strip().lower()
        
        # Check if drugs exist in drug_details_df
        drug1_exists = not drug_details_df[drug_details_df['drugName'] == drug1].empty
        drug2_exists = not drug_details_df[drug_details_df['drugName'] == drug2].empty
        
        # Search for interaction
        interaction = interaction_df[((interaction_df['Drug 1'] == drug1) & (interaction_df['Drug 2'] == drug2)) | 
                                   ((interaction_df['Drug 1'] == drug2) & (interaction_df['Drug 2'] == drug1))]
        
        # Get drug details if they exist
        if drug1_exists:
            drug1_info = drug_details_df[drug_details_df['drugName'] == drug1].to_dict(orient='records')
        if drug2_exists:
            drug2_info = drug_details_df[drug_details_df['drugName'] == drug2].to_dict(orient='records')
        
        # Handle different scenarios
        if not drug1_exists and not drug2_exists:
            error_message = f"Neither '{drug1}' nor '{drug2}' were found in our database."
        elif not drug1_exists:
            error_message = f"'{drug1}' was not found in our database."
        elif not drug2_exists:
            error_message = f"'{drug2}' was not found in our database."
        elif interaction.empty:
            interaction_description = f"No known interactions found between {drug1} and {drug2}."
        else:
            interaction_description = interaction.iloc[0]['Interaction Description']
            interaction_details = {
                'drug1': drug1,
                'drug2': drug2,
                'description': interaction.iloc[0]['Interaction Description'],
                'severity': 'Moderate',  # You can add severity levels to your database if needed
                'recommendation': 'Consult your healthcare provider before taking these medications together.'
            }
    
    return render_template('interaction_checker.html', 
                         interaction_description=interaction_description,
                         interaction_details=interaction_details,
                         drug1_info=drug1_info,
                         drug2_info=drug2_info,
                         error_message=error_message)

@app.route('/data-entry')
def data_entry():
    return render_template('data_entry.html')

@app.route('/add-drug-data', methods=['POST'])
def add_drug_data():
    try:
        # Get form data for drug details
        drug_name = request.form['drug_name'].strip().lower()
        description = request.form['description']
        side_effects = request.form['side_effects']
        
        # Add to drugs.csv
        new_drug = pd.DataFrame({
            'drugName': [drug_name],
            'description': [description],
            'sideEffects': [side_effects]
        })
        new_drug.to_csv('drugs.csv', mode='a', header=False, index=False)
        
        return jsonify({'success': True, 'message': 'Drug data added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error adding drug data: {str(e)}'})

@app.route('/add-interaction-data', methods=['POST'])
def add_interaction_data():
    try:
        # Get form data for interaction
        drug1 = request.form['drug1'].strip().lower()
        drug2 = request.form['drug2'].strip().lower()
        interaction_description = request.form['interaction_description']
        
        # Add to db_drug_interactions.csv
        new_interaction = pd.DataFrame({
            'Drug 1': [drug1],
            'Drug 2': [drug2],
            'Interaction Description': [interaction_description]
        })
        new_interaction.to_csv('db_drug_interactions.csv', mode='a', header=False, index=False)
        
        return jsonify({'success': True, 'message': 'Interaction data added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error adding interaction data: {str(e)}'})

@app.route('/add-multiple-drugs', methods=['POST'])
def add_multiple_drugs():
    try:
        # Get the JSON data containing multiple drugs
        drugs_data = request.json.get('drugs', [])
        
        # Convert to DataFrame
        new_drugs = pd.DataFrame(drugs_data)
        
        # Ensure all drug names are lowercase
        new_drugs['drugName'] = new_drugs['drugName'].str.lower()
        
        # Add to drugs.csv
        new_drugs.to_csv('drugs.csv', mode='a', header=False, index=False)
        
        return jsonify({'success': True, 'message': f'Successfully added {len(drugs_data)} drugs'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error adding drugs: {str(e)}'})

@app.route('/add-multiple-interactions', methods=['POST'])
def add_multiple_interactions():
    try:
        # Get the JSON data containing multiple interactions
        interactions_data = request.json.get('interactions', [])
        
        # Convert to DataFrame
        new_interactions = pd.DataFrame(interactions_data)
        
        # Ensure all drug names are lowercase
        new_interactions['Drug 1'] = new_interactions['Drug 1'].str.lower()
        new_interactions['Drug 2'] = new_interactions['Drug 2'].str.lower()
        
        # Add to db_drug_interactions.csv
        new_interactions.to_csv('db_drug_interactions.csv', mode='a', header=False, index=False)
        
        return jsonify({'success': True, 'message': f'Successfully added {len(interactions_data)} interactions'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error adding interactions: {str(e)}'})

# API Endpoint to handle AI processing via Ollama
@app.route('/process_prompt', methods=['POST'])
def process_prompt():
    data = request.json
    prompt = data.get('prompt', '').lower()
    
    if not prompt:
        return jsonify({'response': 'Please ask me a question!'})

    try:
        # Check if it's a greeting (whole-word match)
        import re
        greeting_pattern = re.compile(r'\b(?:hi|hello|hey|hai|greetings)\b', re.IGNORECASE)
        is_greeting = bool(greeting_pattern.search(prompt))
        
        if is_greeting:
            greeting = "Hello! It's wonderful to meet you! I'm Nova, your medication interaction assistant. "
            if "patient context" in prompt:
                greeting += "I see you've shared your health information with me. I'll keep your specific conditions and medications in mind while answering your questions. How can I help you today?"
            else:
                greeting += "I'm here to help you understand drug interactions and provide medication safety information. How can I assist you today?"
            return jsonify({'response': greeting})

        # Non-greeting → hand off to Ollama
        enhanced_prompt = f"""As Nova, respond to: {prompt}

        Guidelines for response:
        - Keep the response under 72 words
        - Focus on the most critical information
        - Use simple, clear language
        - If the prompt mentions specific drugs:
          * Prioritize information about those drugs
          * Focus on relevant effects and interactions
          * Maintain medical accuracy
        - End with a relevant safety note if space allows"""
        
        response = ollama.chat(model='mistral', messages=[{
            'role': 'user',
            'content': enhanced_prompt
        }])
        ai_response = response['message']['content']
        formatted = ai_response.replace('\n\n', '<br>').replace('\n', '<br>')
        return jsonify({'response': formatted})

    except Exception as e:
        return jsonify({'response': 'I encountered an error. Please try asking your question again.'})


@app.route('/get-drug-info')
def get_drug_info():
    drug_name = request.args.get('name', '').lower()
    if drug_details_df is not None and drug_name:
        drug_info = drug_details_df[drug_details_df['drugName'] == drug_name]
        if not drug_info.empty:
            return jsonify({
                'name': drug_name,
                'description': drug_info.iloc[0]['description'],
                'sideEffects': drug_info.iloc[0]['sideEffects']
            })
    return jsonify({'error': 'Drug not found'})

@app.route('/get-recommendations', methods=['POST'])
def get_recommendations():
    try:
        data = request.json
        age = int(data.get('age'))
        medical_conditions = [cond.lower().strip() for cond in data.get('medicalConditions', [])]
        medications = [med.lower() for med in data.get('medications', [])]

        recommendations = []
        interactions = []

        # Check drug interactions for all medication pairs
        if len(medications) > 1 and interaction_df is not None:
            for i in range(len(medications)):
                for j in range(i + 1, len(medications)):
                    drug1, drug2 = medications[i], medications[j]
                    interaction = interaction_df[
                        ((interaction_df['Drug 1'] == drug1) & (interaction_df['Drug 2'] == drug2)) |
                        ((interaction_df['Drug 1'] == drug2) & (interaction_df['Drug 2'] == drug1))
                    ]
                    if not interaction.empty:
                        interactions.append(f"Please consult your healthcare provider about using {drug1} and {drug2} together, as they may interact.")

        # Get condition-specific recommendations
        for condition in medical_conditions:
            if "diabetes" in condition:
                recommendations.extend([
                    "Monitor blood sugar levels regularly while taking these medications",
                    "Continue diabetes medications as prescribed by your doctor",
                    "Report any unusual changes in blood sugar levels to your healthcare provider"
                ])
            elif "hypertension" in condition:
                recommendations.extend([
                    "Continue blood pressure medications as prescribed",
                    "Monitor your blood pressure regularly",
                    "Report any significant changes in blood pressure to your doctor"
                ])
            elif "heart" in condition:
                recommendations.extend([
                    "Continue cardiac medications as prescribed by your healthcare provider",
                    "Monitor for any changes in heart symptoms",
                    "Regular follow-up with your cardiologist is recommended"
                ])
            elif "asthma" in condition:
                recommendations.extend([
                    "Keep rescue inhalers readily available",
                    "Continue using prescribed asthma medications",
                    "Monitor breathing symptoms and seek immediate care if they worsen"
                ])
            elif "arthritis" in condition:
                recommendations.extend([
                    "Continue prescribed anti-inflammatory medications",
                    "Monitor for any increased joint pain or swelling",
                    "Regular follow-up with your rheumatologist is recommended"
                ])
            elif "thyroid" in condition:
                recommendations.extend([
                    "Continue thyroid medications as prescribed",
                    "Take thyroid medication on an empty stomach",
                    "Regular thyroid function monitoring is recommended"
                ])

        # Add medication-specific recommendations
        for medication in medications:
            if drug_details_df is not None:
                drug_info = drug_details_df[drug_details_df['drugName'] == medication]
                if not drug_info.empty:
                    side_effects = drug_info.iloc[0]['sideEffects']
                    recommendations.append(f"Continue {medication} as prescribed by your healthcare provider")
                    if side_effects:
                        recommendations.append(f"Monitor for these potential effects with {medication}: {side_effects}")

        # If no specific recommendations were generated
        if not recommendations:
            recommendations.append("Continue your medications as prescribed and maintain regular check-ups with your healthcare provider")

        # Remove any duplicate recommendations
        recommendations = list(dict.fromkeys(recommendations))

        # Generate the interaction checker URL with patient details
        interaction_checker_url = url_for('interaction_checker', 
                                        age=age,
                                        conditions=','.join(medical_conditions),
                                        medications=medications)

        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'interactions': '; '.join(interactions) if interactions else None,
            'interactionCheckerUrl': interaction_checker_url
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating recommendations: {str(e)}'
        })

if __name__ == '__main__':
    app.run(debug=True)
