help:
	@echo "Available targets:\n\
		clean - remove build files and directories\n\
		lint  - run code formatters and linters\n\
		test  - run automated test suite\n\
	"

clean:
	bin/clean.sh

check:
	@bin/check.sh

lint: check
	bin/lint.sh

test: check
	bin/test.sh
