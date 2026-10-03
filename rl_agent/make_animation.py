#!/usr/bin/env python3
"""
make_animation.py

Run a short episode with the trained policy and a NetAnim trace enabled, then
copy the resulting XML into docu for the defence. The trace is short on purpose
so the file stays small and loads quickly.

Usage:
    venv/bin/python rl_agent/make_animation.py --model <path-to-model.zip>
"""

import os
import sys
import shutil
import argparse

REPO = "/home/ksschkw/Projects/fyp"
SIM_DIR = os.path.join(REPO, "ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp")
DEFAULT_MODEL = os.path.join(SIM_DIR, "ppo_marl_multi_v2.zip")
OUT_XML = os.path.join(REPO, "docu/m5-evaluation/results/marl-multi-animation.xml")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--duration", type=float, default=6.0)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    from stable_baselines3 import PPO
    sys.path.insert(0, os.path.join(REPO, "rl_agent"))
    from marl_multi_env import MarlMultiEnv

    os.chdir(SIM_DIR)
    env = MarlMultiEnv(port=0, stepTime=0.1, startSim=True, simSeed=args.seed,
                       debug=False,
                       simArgs={"--duration": args.duration, "--anim": 1,
                                "--flowmon": 0})
    model = PPO.load(args.model)
    obs, _ = env.reset()
    done = False
    steps = 0
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, _reward, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
        steps += 1
    env.close()

    src = os.path.join(REPO, "ns-3-dev/marl-multi-animation.xml")
    os.makedirs(os.path.dirname(OUT_XML), exist_ok=True)
    shutil.copyfile(src, OUT_XML)
    print("Ran %d steps. Animation written to %s" % (steps, OUT_XML))
    print("Open it with:")
    print("  /home/ksschkw/Projects/fyp/netanim/build/netanim %s" % OUT_XML)


if __name__ == "__main__":
    main()
