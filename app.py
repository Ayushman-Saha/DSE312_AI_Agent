import streamlit as st
import os
import re
from pypdf import PdfReader
from google import genai
from google.genai import types

client = genai.Client()


def read_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text()
        return text_content
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None


def generate_mcq_questions(pdf_text, n):
    model = "gemini-2.5-flash-lite"
    prompt = f"""
    Based on the following course slides text, generate {n} multiple-choice questions (MCQs)
    with four options and the correct answer
    Assign reasonable marks (2–3). 

     ---
    Course Slides Text:
    {pdf_text}
    ---

    Format strictly as:

    1. Question text? [Marks: 2]
       A) Option A
       B) Option B
       C) Option C
       D) Option D
       Correct Answer: B
    """
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["TEXT"])
    )
    return response.text


def generate_long_answer_questions(pdf_text, n):
    model = "gemini-2.5-flash-lite"
    prompt = f"""
    Based on the following course slides text, Generate {n} long-answer descriptive questions requiring explanations.
    Assign reasonable marks (5–10). No answers.    
     ---
    Course Slides Text:
    {pdf_text}
    ---

    Format strictly as:

    1. Question text? [Marks: 8]
    """
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["TEXT"])
    )
    return response.text


def generate_programming_questions(pdf_text, n):
    model = "gemini-2.5-flash-lite"
    prompt = f"""
    Based on the following course slides text, Generate {n} programming assignment questions
    Assign reasonable marks (5–15). No answers.    
     ---
    Course Slides Text:
    {pdf_text}
    ---

    Format strictly as:

    1. Write a program to ... [Marks: 10]
    """
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["TEXT"])
    )
    return response.text


def extract_marks_from_question(question_text):
    match = re.search(r'\[Marks:\s*(\d+)\]', question_text)
    return int(match.group(1)) if match else 0


def check_mcq_answer(questions_text, question_number, user_answer):
    pattern = rf"{question_number}\..*?Correct Answer: ([A-D])"
    match = re.search(pattern, questions_text, re.DOTALL)
    if match:
        return user_answer.upper() == match.group(1)
    return False


def get_correct_mcq_answer(questions_text, question_number):
    pattern = rf"{question_number}\..*?Correct Answer: ([A-D])"
    match = re.search(pattern, questions_text, re.DOTALL)
    return match.group(1) if match else None


def extract_suggested_marks(ai_response, max_marks):
    patterns = [
        r'[Ss]uggested marks?:?\s*(\d+)(?:/\d+)?',
        r'[Mm]ards?:?\s*(\d+)(?:\s*out of\s*\d+)?',
        r'[Ss]core:?\s*(\d+)(?:/\d+)?',
        r'[Gg]rade:?\s*(\d+)(?:/\d+)?',
        r'(\d+)\s*marks?\s*out of',
        r'(\d+)\s*/\s*\d+\s*marks?',
        r'award\s*(\d+)\s*marks?',
        r'give\s*(\d+)\s*marks?'
    ]

    for pattern in patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            suggested = int(match.group(1))
            return min(suggested, max_marks)  # Don't exceed max marks

    return 0  # Default to 0 if no marks found


def evaluate_long_answer(question, student_answer):
    model = "gemini-2.5-flash-lite"
    max_marks = extract_marks_from_question(question)
    prompt = f"""
    You are grading a student's descriptive answer. Evaluate correctness and completeness.
    The question is worth {max_marks} marks total.

    Question:
    {question}

    Answer:
    {student_answer}

    Please provide:
    1. Brief feedback on the answer quality
    2. Suggested marks: X/{max_marks} (be specific with the number)
    3. Areas for improvement (if any)

    Format your response clearly and include "Suggested marks: X/{max_marks}" in your feedback.
    """
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["TEXT"])
    )
    return response.text


def analyze_programming(question, student_code):
    model = "gemini-2.5-flash-lite"
    max_marks = extract_marks_from_question(question)
    prompt = f"""
    Analyze the following student code logically (do not run).
    The question is worth {max_marks} marks total.

    Question:
    {question}

    Code:
    {student_code}

    Please provide:
    1. Code logic analysis
    2. Suggested marks: X/{max_marks} (be specific with the number)
    3. Areas for improvement

    Format your response clearly and include "Suggested marks: X/{max_marks}" in your feedback.
    """
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["TEXT"])
    )
    return response.text


def calculate_statistics():
    """Calculate comprehensive statistics for the evaluation"""
    if "evaluation_results" not in st.session_state:
        return None

    results = st.session_state["evaluation_results"]
    assignment = st.session_state["assignment"]

    stats = {
        "mcq": {"attempted": 0, "correct": 0, "total": 0, "marks_obtained": 0, "total_marks": 0},
        "long": {"attempted": 0, "total": 0, "marks_obtained": 0, "total_marks": 0},
        "prog": {"attempted": 0, "total": 0, "marks_obtained": 0, "total_marks": 0}
    }

    # MCQ Stats
    mcq_lines = [line for line in assignment["mcqs"].split('\n') if line.strip() and re.match(r'^\d+\.', line.strip())]
    stats["mcq"]["total"] = len(mcq_lines)

    for i in range(1, len(mcq_lines) + 1):
        if f"mcq{i}" in results:
            stats["mcq"]["attempted"] += 1
            marks = extract_marks_from_question(mcq_lines[i - 1])
            stats["mcq"]["total_marks"] += marks
            if results[f"mcq{i}"]["correct"]:
                stats["mcq"]["correct"] += 1
                stats["mcq"]["marks_obtained"] += marks

    # Long Answer Stats
    long_lines = [line for line in assignment["longs"].split('\n') if
                  line.strip() and re.match(r'^\d+\.', line.strip())]
    stats["long"]["total"] = len(long_lines)

    for i in range(1, len(long_lines) + 1):
        if f"long{i}" in results:
            stats["long"]["attempted"] += 1
            marks = extract_marks_from_question(long_lines[i - 1])
            stats["long"]["total_marks"] += marks
            override_marks = st.session_state.get(f"override{i}", 0)
            stats["long"]["marks_obtained"] += override_marks

    # Programming Stats
    prog_lines = [line for line in assignment["progs"].split('\n') if
                  line.strip() and re.match(r'^\d+\.', line.strip())]
    stats["prog"]["total"] = len(prog_lines)

    for i in range(1, len(prog_lines) + 1):
        if f"prog{i}" in results:
            stats["prog"]["attempted"] += 1
            marks = extract_marks_from_question(prog_lines[i - 1])
            stats["prog"]["total_marks"] += marks
            final_marks = st.session_state.get(f"progmarks{i}", 0)
            stats["prog"]["marks_obtained"] += final_marks

    return stats


st.set_page_config(page_title="AI Assignment System", layout="wide")
st.title("AI-Powered Assignment System")

if "evaluation_results" not in st.session_state:
    st.session_state["evaluation_results"] = {}

generator_tab, attempt_tab, evaluator_tab = st.tabs(["Assignment Generator", "Attempt", "Evaluation"])

with generator_tab:
    st.header("Generate Assignment")
    uploaded_file = st.file_uploader("Upload Course Slides (PDF)", type=["pdf"])

    col1, col2, col3 = st.columns(3)
    with col1:
        mcq_count = st.number_input("Number of MCQs", 1, 10, 3)
    with col2:
        long_count = st.number_input("Number of Long Answer Questions", 1, 5, 2)
    with col3:
        prog_count = st.number_input("Number of Programming Questions", 1, 5, 2)

    if uploaded_file and st.button("Generate Assignment", type="primary"):
        with st.spinner("Generating assignment..."):
            with open("temp.pdf", "wb") as f:
                f.write(uploaded_file.read())
            slides_text = read_pdf("temp.pdf")

            if slides_text:
                st.subheader("Generated Questions")

                mcqs = generate_mcq_questions(slides_text, mcq_count)
                st.markdown("### Multiple Choice Questions")
                st.text(mcqs)

                longs = generate_long_answer_questions(slides_text, long_count)
                st.markdown("###  Long Answer Questions")
                st.text(longs)

                progs = generate_programming_questions(slides_text, prog_count)
                st.markdown("###  Programming Questions")
                st.text(progs)

                st.session_state["assignment"] = {"mcqs": mcqs, "longs": longs, "progs": progs}
                st.success("Assignment generated successfully! Go to the 'Attempt' tab to start.")

with attempt_tab:
    if "assignment" not in st.session_state:
        st.info("Please generate an assignment first in the 'Assignment Generator' tab.")
    else:
        st.header("Attempt Assignment")
        assignment = st.session_state["assignment"]

        st.subheader("Multiple Choice Questions")
        mcq_blocks = assignment["mcqs"].split("Correct Answer")
        mcq_questions = []

        for i, q_block in enumerate(mcq_blocks[:-1], start=1):
            question_text = q_block.strip()
            st.markdown(f"Question {i}:")
            st.markdown(question_text[3:])
            answer = st.radio(f"Select your answer for Question {i}:", ["A", "B", "C", "D"],
                              key=f"mcq{i}", index=None)
            mcq_questions.append(question_text)
            st.divider()

        # Long Answer Section
        st.subheader("Long Answer Questions")
        long_questions = [q.strip() for q in assignment["longs"].split("\n") if
                          q.strip() and re.match(r'^\d+\.', q.strip())]

        for i, q in enumerate(long_questions, start=1):
            st.markdown(f"Question {i}:")
            st.markdown(q)
            st.text_area(f"Your Answer for Question {i}:", key=f"long{i}", height=150)
            st.divider()

        st.subheader("Programming Questions")
        prog_questions = [q.strip() for q in assignment["progs"].split("\n") if
                          q.strip() and re.match(r'^\d+\.', q.strip())]

        for i, q in enumerate(prog_questions, start=1):
            st.markdown(f"Question {i}:")
            st.markdown(q)
            st.text_area(f"Submit your code for Question {i}:", key=f"prog{i}", height=200)
            st.divider()

        # Evaluate Button
        st.markdown("---")
        if st.button("🔍 Evaluate Assignment", type="primary", use_container_width=True):
            with st.spinner("Evaluating your assignment..."):
                evaluation_results = {}

                for i in range(1, len(mcq_blocks)):
                    user_answer = st.session_state.get(f"mcq{i}")
                    if user_answer:
                        correct = check_mcq_answer(assignment["mcqs"], i, user_answer)
                        correct_answer = get_correct_mcq_answer(assignment["mcqs"], i)
                        evaluation_results[f"mcq{i}"] = {
                            "attempted": True,
                            "user_answer": user_answer,
                            "correct_answer": correct_answer,
                            "correct": correct
                        }

                for i, q in enumerate(long_questions, start=1):
                    user_answer = st.session_state.get(f"long{i}")
                    if user_answer and user_answer.strip():
                        feedback = evaluate_long_answer(q, user_answer)
                        max_marks = extract_marks_from_question(q)
                        suggested_marks = extract_suggested_marks(feedback, max_marks)
                        evaluation_results[f"long{i}"] = {
                            "attempted": True,
                            "question": q,
                            "user_answer": user_answer,
                            "feedback": feedback,
                            "suggested_marks": suggested_marks
                        }
                        if f"override{i}" not in st.session_state:
                            st.session_state[f"override{i}"] = suggested_marks

                for i, q in enumerate(prog_questions, start=1):
                    user_code = st.session_state.get(f"prog{i}")
                    if user_code and user_code.strip():
                        feedback = analyze_programming(q, user_code)
                        max_marks = extract_marks_from_question(q)
                        suggested_marks = extract_suggested_marks(feedback, max_marks)
                        evaluation_results[f"prog{i}"] = {
                            "attempted": True,
                            "question": q,
                            "user_code": user_code,
                            "feedback": feedback,
                            "suggested_marks": suggested_marks
                        }
                        if f"progmarks{i}" not in st.session_state:
                            st.session_state[f"progmarks{i}"] = suggested_marks

                st.session_state["evaluation_results"] = evaluation_results
                st.success("Evaluation completed! Check the 'Evaluation' tab for results.")

with evaluator_tab:
    if "assignment" not in st.session_state:
        st.info("Please generate an assignment first in the 'Assignment Generator' tab.")
    elif "evaluation_results" not in st.session_state:
        st.info("Please attempt and evaluate the assignment first in the 'Attempt' tab.")
    else:
        st.header("Assignment Evaluation & Results")

        assignment = st.session_state["assignment"]
        results = st.session_state["evaluation_results"]

        # Statistics Section
        st.subheader("Performance Statistics")
        stats = calculate_statistics()

        if stats:
            col1, col2, col3, col4 = st.columns(4)

            total_attempted = stats["mcq"]["attempted"] + stats["long"]["attempted"] + stats["prog"]["attempted"]
            total_questions = stats["mcq"]["total"] + stats["long"]["total"] + stats["prog"]["total"]
            total_marks_obtained = stats["mcq"]["marks_obtained"] + stats["long"]["marks_obtained"] + stats["prog"][
                "marks_obtained"]
            total_marks_available = stats["mcq"]["total_marks"] + stats["long"]["total_marks"] + stats["prog"][
                "total_marks"]

            with col1:
                st.metric("Questions Attempted", f"{total_attempted}/{total_questions}")
            with col2:
                st.metric("MCQ Accuracy", f"{stats['mcq']['correct']}/{stats['mcq']['attempted']}" if stats['mcq'][
                                                                                                          'attempted'] > 0 else "0/0")
            with col3:
                st.metric("Total Score", f"{total_marks_obtained}/{total_marks_available}")
            with col4:
                percentage = (total_marks_obtained / total_marks_available  * 100) if total_marks_available > 0 else 0
                st.metric("Percentage", f"{percentage:.1f}%")

            st.markdown("#### Section-wise Breakdown")
            breakdown_col1, breakdown_col2, breakdown_col3 = st.columns(3)

            with breakdown_col1:
                st.markdown("MCQs")
                st.write(f"• Attempted: {stats['mcq']['attempted']}/{stats['mcq']['total']}")
                st.write(f"• Correct: {stats['mcq']['correct']}")
                st.write(f"• Marks: {stats['mcq']['marks_obtained']}/{stats['mcq']['total_marks']}")

            with breakdown_col2:
                st.markdown("Long Answers")
                st.write(f"• Attempted: {stats['long']['attempted']}/{stats['long']['total']}")
                st.write(f"• Marks: {stats['long']['marks_obtained']}/{stats['long']['total_marks']}")

            with breakdown_col3:
                st.markdown("Programming")
                st.write(f"• Attempted: {stats['prog']['attempted']}/{stats['prog']['total']}")
                st.write(f"• Marks: {stats['prog']['marks_obtained']}/{stats['prog']['total_marks']}")

        st.markdown("---")

        st.subheader("📝 MCQ Evaluation")
        mcq_blocks = assignment["mcqs"].split("Correct Answer")

        for i in range(1, len(mcq_blocks)):
            question_text = mcq_blocks[i - 1].strip()
            st.markdown(f"Question {i}:")

            with st.container():
                st.markdown(question_text)

            if f"mcq{i}" in results:
                result = results[f"mcq{i}"]
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"Your Answer: {result['user_answer']}")
                    st.write(f"Correct Answer: {result['correct_answer']}")

                with col2:
                    if result["correct"]:
                        st.success("Correct")
                    else:
                        st.error("Incorrect")
            else:
                st.warning("Question not attempted")

            st.divider()

        # Long Answer Evaluation
        st.subheader("Long Answer Evaluation")
        long_questions = [q.strip() for q in assignment["longs"].split("\n") if
                          q.strip() and re.match(r'^\d+\.', q.strip())]

        for i, q in enumerate(long_questions, start=1):
            st.markdown(f"Question {i}: {q}")

            if f"long{i}" in results:
                result = results[f"long{i}"]

                with st.expander(f"View Answer & Feedback for Question {i}"):
                    st.markdown("Your Answer:")
                    st.write(result["user_answer"])

                    st.markdown("AI Feedback:")
                    st.write(result["feedback"])

                # Instructor override for marks
                max_marks = extract_marks_from_question(q)
                default_marks = results[f"long{i}"].get("suggested_marks", 0)
                override_marks = st.number_input(
                    f"Instructor Override Marks for Q{i} (Max: {max_marks}) [AI Suggested: {default_marks}]",
                    0, max_marks,
                    value=st.session_state.get(f"override{i}", default_marks),
                    key=f"override{i}",
                    help=f"AI suggested {default_marks} marks for this answer"
                )
            else:
                st.warning("Question not attempted")

            st.divider()

        st.subheader("Programming Evaluation")
        prog_questions = [q.strip() for q in assignment["progs"].split("\n") if
                          q.strip() and re.match(r'^\d+\.', q.strip())]

        for i, q in enumerate(prog_questions, start=1):
            st.markdown(f"Question {i}: {q}")

            if f"prog{i}" in results:
                result = results[f"prog{i}"]

                with st.expander(f"View Code & Analysis for Question {i}"):
                    st.markdown("Submitted Code:")
                    st.code(result["user_code"], language="python")

                    st.markdown("AI Analysis:")
                    st.write(result["feedback"])

                # Instructor final marks
                max_marks = extract_marks_from_question(q)
                default_marks = results[f"prog{i}"].get("suggested_marks", 0)
                final_marks = st.number_input(
                    f"Instructor Final Marks for Q{i} (Max: {max_marks}) [AI Suggested: {default_marks}]",
                    0, max_marks,
                    value=st.session_state.get(f"progmarks{i}", default_marks),
                    key=f"progmarks{i}",
                    help=f"AI suggested {default_marks} marks for this code"
                )
            else:
                st.warning("⚠️ Question not attempted")

            st.divider()

        if stats:
            st.markdown("---")
            st.subheader("Final Summary")

            final_percentage = (total_marks_obtained / total_marks_available * 100) if total_marks_available > 0 else 0

            if final_percentage >= 90:
                grade_text = "Excellent"
            elif final_percentage >= 75:
                grade_text = "Good"
            elif final_percentage >= 60:
                grade_text = "Average"
            else:
                grade_text = "Needs Improvement"

            st.markdown(f"""
            Overall Performance:{grade_text}

            Final Score: {total_marks_obtained}/{total_marks_available} ({final_percentage:.1f}%)

            Completion Rate: {total_attempted}/{total_questions} questions attempted
            """)

            if total_attempted < total_questions:
                st.info(
                    f"Tip: You have {total_questions - total_attempted} unattempted questions. Consider completing them for a better score!")

# Clean up temp file
if os.path.exists("temp.pdf"):
    try:
        os.remove("temp.pdf")
    except:
        pass