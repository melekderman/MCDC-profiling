import argparse
import os
import sys
import yaml

from pathlib import Path

# For future extension if multiple platforms are needed
PLATFORMS = ["dane"]

JOB_SUBMISSION = {}
JOB_SUBMISSION["dane"] = 'sbatch'

JOB_SCHEDULER = {}
JOB_SCHEDULER["dane"] = 'slurm'

# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(description="MC/DC Profiling Test Suite")
parser.add_argument("--name", type=str, default="ALL", help="Name of the task to run")
parser.add_argument("--N_particle", type=lambda x: int(float(x)), default=None,
                    help="Number of particles")
parser.add_argument("--Time", type=lambda x: int(float(x)), default=None,
                    help="Time")
parser.add_argument("--profile_tool", type=str, choices=["cProfile"], default="cProfile",
                    help="Profiling tool to use (default: cProfile)")
parser.add_argument("--mode", type=str, choices=["python", "numba"], default="python",
                    help="Select the mode to run (default: python)")
parser.add_argument("--platform", type=str, required=False, choices=PLATFORMS, default="dane",
                    help="Platform to run the tests on")
parser.add_argument("--output_folder", default=False, action="store_true",
                    help="Save the results to a folder")
parser.add_argument("--save_recent_output", default=False, action="store_true",
                    help="If set True, keep the .prof file. Otherwise, it will be removed after generating the PNG.")
args, unargs = parser.parse_known_args()

# Get the platform-specific job submission and scheduler commands
platform = args.platform
job_submission = JOB_SUBMISSION[platform]
job_scheduler = JOB_SCHEDULER[platform]

# ======================================================================================
# Preparation
# ======================================================================================

# Get the base directory
base_dir = os.getcwd()

# Read the PBS template
template_path = os.path.join(base_dir, "template.pbs")
with open(template_path, 'r') as f:
    pbs_template = f.read()

# Read the tasks
task_yaml_path = os.path.join(base_dir, "task.yaml")
with open(task_yaml_path, "r") as file:
    tasks = yaml.safe_load(file)

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
    if args.mode == "python":
        task = tasks[problem]["python"]
    else:
        sys.exit("[ERROR] Only python mode is currently supported.")

    if args.N_particle is not None:
        N_particle = args.N_particle
    else:
        N_particle = task["N_particle"]

    if args.Time is not None:
        job_time = args.Time
    else:
        job_time = task["Time"]

    # Decide on output file paths based on the --output_folder argument
    if args.output_folder:
        prof_file = os.path.join(output_dir, f"output_{problem}_{N_particle}p.prof")
        png_file = os.path.join(output_dir, f"profile_{problem}_{N_particle}p.png")
    else:
        prof_file = f"output_{N_particle}p.prof"
        png_file = f"profile_{N_particle}p.png"

    # Build the profiling command based on the selected profiling tool
    # (only cProfile option for now)
    if args.profile_tool != "cProfile":
        sys.exit("[ERROR] Only cProfile is currently supported.")

    cmd_prof = f"python -m cProfile -o {prof_file} input.py --mode={args.mode}\n"

    # Build the commands string
    commands = ""
    commands += cmd_prof
    commands += f"gprof2dot -f pstats --colour-nodes-by-selftime {prof_file}"
    commands += f" | dot -Tpng -o {png_file}\n"

    if not args.save_recent_output:
        commands += f"rm {prof_file}\n"

    # Create the PBS file by replacing placeholders in the template
    pbs_text = pbs_template[:]
    pbs_text = pbs_text.replace("<N_NODE>", "1")
    pbs_text = pbs_text.replace("<JOB_NAME>", f"profile-{args.mode}-{problem}")
    pbs_text = pbs_text.replace("<TIME>", job_time)
    pbs_text = pbs_text.replace("<CASE>", f"{problem}")
    pbs_text = pbs_text.replace("<COMMANDS>", commands)

    # Write the PBS file in the problem folder
    with open("submit.pbs", "w") as f:
        f.write(pbs_text)

    # Submit the job
    os.system(f"{job_submission} submit.pbs")
    
    # Delete the PBS file
    os.remove("submit.pbs")

    # Return to the base directory before processing the next problem
    os.chdir(base_dir)
