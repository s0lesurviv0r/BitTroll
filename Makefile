prereqs:
	prereqs.sh

dist:
	pyinstaller --onefile main.py
	cp config.sample.json dist/.

clean:
	rm -Rf build
	rm -Rf dist
