import argparse
import os
import yaml

from pathlib import Path

# For future extension if multiple platforms are needed
PLATFORMS = ["dane"]

JOB_SUBMISSION = {}
JOB_SUBMISSION["dane"] = 'sbatch'

JOB_SCHEDULER = {}
JOB_SCHEDULER["dane"] = 'slurm'

JOB_TIME = {}
JOB_TIME['dane'] = "24:00:00"

# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(description="MC/DC Profiling Test Suite")
parser.add_argument("--name", type=str, default="ALL", help="Name of the task to run")
parser.add_argument("--profile_tool", type=str, choices=["cProfile"], default="cProfile",
                    help="Profiling tool to use (default: cProfile)")
parser.add_argument("--mode", type=str, choices=["python", "numba"], default="python",
                    help="Select the mode to run (default: python)")
parser.add_argument("--platform", type=str, required=False, choices=PLATFORMS, default="dane",
                    help="Platform to run the tests on")
parser.add_argument("--output_folder", default=False, action="output_folder_true",
                    help="Save the results to a folder")
args, unargs = parser.parse_known_args()

# ======================================================================================
# Platform settings
# ======================================================================================

platform = args.platform
job_submission = JOB_SUBMISSION[platform]
job_scheduler = JOB_SCHEDULER[platform]
job_time = JOB_TIME[platform]

# Get the PBS template
with open("template.pbs", 'r') as f:
    pbs_template = f.read()

# ======================================================================================
# Preparation
# ======================================================================================

# Read the tasks
os.chdir("../../../")
with open("task.yaml", "r") as file:
    tasks = yaml.safe_load(file)

base_dir = os.getcwd()

# If --output_folder is set, create a top-level folder "output"
if args.output_folder:
    output_dir = os.path.join(base_dir, "output")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

# Check if specified --name is listed in the task
if args.name != "ALL" and args.name not in tasks:
    print(f"[ERROR] Specified problem name {args.name} is not in the task list.")
    exit()

# ======================================================================================
# Run the tests
# ======================================================================================

# Loop over the problems
for problem in tasks:
    # If --name is specified, skip other problems.
    if args.name != "ALL" and problem != args.name:
        continue

    # Change into the problem folder
    problem_dir = os.path.join(base_dir, "test_suite", problem)
    os.chdir(problem_dir)

    # Task parameters
    task = tasks[problem]
    N_particle = task["N_particle"]
    N_batch = task["N_batch"]
    P_Time = task["Time"]

    # Decide on output file paths based on the output_folder argument
    if args.output_folder:
        prof_file = os.path.join(output_dir, f"output_{problem}_{N_particle}p_{N_batch}b.prof")
        png_file = os.path.join(output_dir, f"profile_{problem}_{N_particle}p_{N_batch}b.png")
    else:
        prof_file = f"output_{N_particle}p_{N_batch}b.prof"
        png_file = f"profile_{N_particle}p_{N_batch}b.png"