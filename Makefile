help:
	@echo "Available targets:\n\
		clean - remove build files and directories\n\
		lint  - run code formatters and linters\n\
		test  - run automated test suite\n\
		run   - compute calculated ratings for all rating scales\n\
		dist  - build archive containing all calculated ratings\n\
	"

clean:
	bin/clean.sh

check:
	@bin/check.sh

lint: check
	bin/lint.sh

test: check
	bin/test.sh

run: check
	bin/run.sh

dist: check clean
	bin/dist.sh
