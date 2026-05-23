.PHONY: install server tray train extract-frames help

install:
	bash install.sh

server:
	bash start-server.sh

server-debug:
	bash start-server.sh --conf 0.25

tray:
	bash start-tray.sh

train:
	conda run --no-capture-output -n yolo python src/train/train.py --config configs/train.yaml

train-resume:
	conda run --no-capture-output -n yolo python src/train/train.py --config configs/train.yaml --resume

extract-frames:
	conda run --no-capture-output -n yolo python src/collect/extract_frames.py data/raw/ --fps 1

lint:
	ruff check src/ && ruff format --check src/

help:
	@echo "make install        — set up conda env and dependencies"
	@echo "make tray           — start the system-tray GUI launcher"
	@echo "make server         — start the WebSocket inference server (conf=0.5)"
	@echo "make server-debug   — start server with lower conf threshold (conf=0.25)"
	@echo "make train          — train from configs/train.yaml"
	@echo "make train-resume   — resume interrupted training"
	@echo "make extract-frames — extract frames from data/raw/ at 1 fps"
	@echo "make lint           — run ruff linter + format check"
