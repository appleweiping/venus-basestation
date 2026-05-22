# 1. Define SOURCES early so the sync target can see them
SOURCES := $(wildcard *.c)

# 2. Put 'sync' at the top so it becomes the default 'make' command
.PHONY: sync
sync:
	@echo "Touching files to fix Pynq clock skew..."
	@find . -type f -exec touch {} +
	@sleep 1
	@touch $(SOURCES)
	@$(MAKE) all

# 3. Include your shared logic
include ../shared.mk

# CFLAGS+=-Werror

# 4. Include the end logic
include ../end.mk