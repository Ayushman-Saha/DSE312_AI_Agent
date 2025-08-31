import os
import re
import subprocess
from datetime import date

from google import genai
from google.genai import types
from pypdf import PdfReader

os.environ['GOOGLE_API_KEY'] = 'NOT FOR PUBLIC DISPLAY'
client = genai.Client()

def read_pdf(file_path):
    """
    Reads a PDF file and extracts all text from it.
    Args:
        file_path (str): The path to the PDF file.
    Returns:
        str: All text extracted from the PDF.
    """
    try:
        reader = PdfReader(file_path)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text()
        return text_content
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

def generate_questions(pdf_text):
    """
    Uses the Gemini Pro model to generate MCQ and programming questions
    from the provided PDF text.
    Args:
        pdf_text (str): The text content extracted from the PDF.
    Returns:
        str: The generated questions from the model.
    """

    # Initialize the model
    model = "gemini-2.5-flash-lite"

    prompt = f"""
    Based on the following course slides text, generate a few multiple-choice questions (MCQs)
    with four options and the correct answer, and a few programming questions. 
    Do not add any explaination based questions. Do not add correct answer for programming assignment
    Assign a reasonable number of marks to each question.

    ---
    Course Slides Text:
    {pdf_text}
    ---

    Format the output as follows:

    ### Multiple-Choice Questions
    1. Question text? [Marks: 2]
       A) Option A
       B) Option B
       C) Option C
       D) Option D
       Correct Answer: B

    2. ... [Marks: 3]

    ### Programming Questions
    1. Write a program to...[Marks: 5]
    2. ... [Marks: 10]
    """

    try:
        response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT']
            )
        )
        return response.text
    except Exception as e:
        print(f"Error generating content with Gemini API: {e}")
        return None


def parse_questions_with_marks(questions_text):
    """
    Parses the generated questions text to extract questions and their marks,
    and calculates the total marks.
    Args:
        questions_text (str): The full text of the generated questions.
    Returns:
        tuple: A tuple containing the cleaned question text (without marks)
               and the total marks.
    """
    total_marks = 0
    cleaned_questions_text = questions_text

    # Regex to find all instances of `[Marks: X]`
    marks_pattern = r'\[Marks: (\d+)\]'
    matches = re.finditer(marks_pattern, questions_text)

    for match in matches:
        marks = int(match.group(1))
        total_marks += marks

    # Remove all `[Marks: X]` from the text for a clean output
    cleaned_questions_text = re.sub(marks_pattern, '', cleaned_questions_text)

    return cleaned_questions_text, total_marks



def check_mcq_answer(questions_text, question_number, user_answer):
    """
    Checks if a user's answer to an MCQ is correct.
    Args:
        questions_text (str): The full text of the generated questions.
        question_number (int): The number of the question to check.
        user_answer (str): The user's answer (e.g., 'A', 'B', 'C', 'D').
    Returns:
        bool: True if the answer is correct, False otherwise.
    """
    pattern = rf"{question_number}\..*?Correct Answer: ([A-D])"
    match = re.search(pattern, questions_text, re.DOTALL)
    if match:
        correct_answer = match.group(1)
        return user_answer.upper() == correct_answer.upper()
    return False

import os
from google import genai
from google.genai import types

# Configure the Gemini API with your key
os.environ['GOOGLE_API_KEY'] = 'AIzaSyAg-UI7eAxiTI-ROU0qROR5qCZ9NUmLAK4'
client = genai.Client()


def get_initial_analysis(question, student_code):
    """
    Performs a logical analysis of the student's code using Gemini.
    """
    model = "gemini-2.5-flash-lite"
    prompt = f"""
    You are an AI grader for a computer vision course. A student has submitted code for a problem.
    Your task is to analyze the logic of their code. Do not execute the code.

    Based on the provided question and the student's code, provide the following:
    1. A brief summary of what the student's code appears to be doing logically.
    2. A preliminary assessment of whether the code's logic correctly implements the required algorithm.

    ---
    Programming Question:
    {question}

    ---
    Student's Code:
    ```python
    {student_code}
    ```
    """
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT']
            )
        )
        return response.text
    except Exception as e:
        return f"Error during initial analysis with Gemini API: {e}"

def generate_long_answer_questions(pdf_text):
    """
    Uses the Gemini model to generate descriptive long-answer questions
    from the provided PDF text.
    Args:
        pdf_text (str): The text content extracted from the PDF.
    Returns:
        str: The generated long-answer questions.
    """
    model = "gemini-2.5-flash-lite"
    prompt = f"""
    Based on the following course slides text, generate 3–5 descriptive long-answer questions.
    - Each question should require a detailed explanation or derivation.
    - Assign a reasonable number of marks (e.g., 5–10).
    - Do not provide answers, only questions.

    ---
    Course Slides Text:
    {pdf_text}
    ---

    Format the output as follows:

    ### Long-Answer Questions
    1. Question text? [Marks: 5]
    2. Question text? [Marks: 8]
    3. ...
    """

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT']
            )
        )
        return response.text
    except Exception as e:
        print(f"Error generating long-answer questions with Gemini API: {e}")
        return None


def evaluate_long_answer(question, student_answer):
    """
    Uses Gemini to evaluate a student's long-answer response logically.
    Args:
        question (str): The original long-answer question.
        student_answer (str): The student's submitted response.
    Returns:
        str: Feedback and a tentative grade.
    """
    model = "gemini-2.5-flash-lite"
    prompt = f"""
    You are grading a student's descriptive answer. Evaluate the quality, correctness,
    and completeness of their response. Assign marks out of the total available
    based on the question.

    ---
    Question:
    {question}

    ---
    Student's Answer:
    {student_answer}
    """

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT']
            )
        )
        return response.text
    except Exception as e:
        return f"Error evaluating long-answer with Gemini API: {e}"





if __name__ == "__main__":
    pdf_file_path = "lecture.pdf"  # Replace with the path to your PDF file
    if not os.path.exists(pdf_file_path):
        print(f"Error: The file '{pdf_file_path}' was not found.")
    else:
        print("Reading PDF file...")
        slides_text = read_pdf(pdf_file_path)
        if slides_text:
            print("Generating questions with Gemini API...")
            questions = generate_questions(slides_text)
            if questions:
                print("\n--- Generated Questions ---")
                print(questions)

                # Part 1: Parse and calculate total marks
                cleaned_questions, max_marks = parse_questions_with_marks(questions)
                print(f"Total calculated maximum marks: {max_marks} 💯")

                # Part 2: Generate LaTeX file with the new max_marks
                course_info = {
                    "course_code": "DSE312",
                    "assignment_number": 1,
                    "date": date.today().strftime("%B %d, %Y")
                }

                # Part 3: Demonstrate MCQ checking
                print("\n--- Checking an MCQ ---")
                question_to_check = 1
                user_provided_answer = 'A'
                is_correct = check_mcq_answer(questions, question_to_check, user_provided_answer)

                if is_correct:
                    print(f"Your answer '{user_provided_answer}' for question {question_to_check} is correct! 🎉")
                else:
                    print(f"Your answer '{user_provided_answer}' for question {question_to_check} is incorrect. 😔")