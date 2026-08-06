# M3 Setup Notes

## M3.0 – ns3‑gym Installation
- Cloned ns3‑gym into `contrib/ns3-gym`, branch `app-ns-3.36+`.
- Manually generated protobuf files with `protoc`.
- Modified `CMakeLists.txt` to include `messages.pb.cc` and disable broken examples.
- Configured with `./ns3 configure --enable-examples` and built successfully.

## M3.1 – Python Environment
- Created venv with `gymnasium`, `stable-baselines3`, `zmq`, `numpy`, `matplotlib`.
- Installed ns3‑gym Python module using `pip install -e .` from `model/ns3gym`.

## M3.2 – Bridge Test
- Ran `opengym-example` and simple Python ZMQ client; bridge works.