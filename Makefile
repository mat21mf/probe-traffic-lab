PY      ?= python3
OUT     ?= data/outputs
SCEN    ?= configs/scenarios/baseline.yaml configs/scenarios/closures.yaml configs/scenarios/sparse.yaml configs/scenarios/noisy.yaml
export PYTHONPATH := prototype

.PHONY: setup test eval core core-test parity golden all clean

setup:
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest -q

eval:
	$(PY) -m probetraffic run $(SCEN) --out $(OUT) --report reports

core:
	mkdir -p core/build
	javac -Xlint:all -d core/build $$(find core/src -name '*.java')

core-test: core
	java -cp core/build lab.probetraffic.GoldenFixtureTest contracts/golden

parity: core
	$(PY) -m probetraffic run configs/scenarios/closures.yaml --out $(OUT) --report data/tmp-report
	$(PY) scripts/parity_check.py $(OUT)/closures --work data/parity

golden: core
	$(PY) scripts/parity_check.py $(OUT)/closures --work data/parity --golden contracts/golden --golden-segments 160

all: test core-test eval parity

clean:
	rm -rf core/build data
