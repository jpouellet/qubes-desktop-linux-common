PREFIX ?= /usr
MANDIR ?= $(PREFIX)/share/man

PANDOC=pandoc -s -f rst -t man

TOOLS_DIR=tools
TOOLS_DOCS=$(patsubst %.rst,%.1.gz,$(wildcard $(TOOLS_DIR)/*.rst))

help:
	@echo "make rst=example.rst preview	-- generate manpage preview from example.rst"
	@echo "make manpages			-- generate manpages"
	@echo "make install			-- generate manpages and copy them to $$MANDIR"

install: manpages
	mkdir -p $(DESTDIR)$(MANDIR)/man1
	install -m644 $(TOOLS_DOCS) $(DESTDIR)$(MANDIR)/man1

%.1: %.rst
	$(PANDOC) $< > $@

%.1.gz: %.1
	gzip -f $<

manpages: $(TOOLS_DOCS)
	
preview: $(rst)
	$(PANDOC) $(rst) | groff -mandoc -Tlatin1 | less -R

clean:
	rm -f $(TOOLS_DOCS)
