const header = document.querySelector(".site-header");
const menuToggle = document.querySelector(".site-nav-toggle");
const navigation = document.querySelector("#site-nav");
const accountMenu = document.querySelector(".account-menu");
const accountToggle = document.querySelector(".account-avatar");

if (header && menuToggle && navigation) {
    header.classList.add("menu-ready");
    let accountMenuCloseTimer;

    const closeAccountMenu = () => {
        if (!accountMenu || !accountToggle) {
            return;
        }
        window.clearTimeout(accountMenuCloseTimer);
        accountMenu.classList.remove("is-open");
        accountToggle.setAttribute("aria-expanded", "false");
    };

    const closeMenu = () => {
        navigation.classList.remove("is-open");
        menuToggle.setAttribute("aria-expanded", "false");
        menuToggle.setAttribute("aria-label", "Abrir menu");
    };

    menuToggle.addEventListener("click", () => {
        const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
        navigation.classList.toggle("is-open", !isOpen);
        menuToggle.setAttribute("aria-expanded", String(!isOpen));
        menuToggle.setAttribute("aria-label", isOpen ? "Abrir menu" : "Fechar menu");
    });

    navigation.addEventListener("click", (event) => {
        if (event.target instanceof Element && event.target.closest("a")) {
            closeAccountMenu();
            closeMenu();
        }
    });

    if (accountMenu && accountToggle) {
        let lastPointerType = null;

        const setAccountMenuOpen = (isOpen) => {
            window.clearTimeout(accountMenuCloseTimer);
            accountMenu.classList.toggle("is-open", isOpen);
            accountToggle.setAttribute("aria-expanded", String(isOpen));
        };

        const scheduleAccountMenuClose = () => {
            window.clearTimeout(accountMenuCloseTimer);
            accountMenuCloseTimer = window.setTimeout(() => {
                closeAccountMenu();
            }, 300);
        };

        accountToggle.addEventListener("pointerdown", (event) => {
            lastPointerType = event.pointerType;
        });

        accountMenu.addEventListener("pointerenter", (event) => {
            if (event.pointerType === "mouse") {
                setAccountMenuOpen(true);
            }
        });

        accountMenu.addEventListener("pointerleave", (event) => {
            if (event.pointerType === "mouse") {
                scheduleAccountMenuClose();
            }
        });

        accountToggle.addEventListener("click", (event) => {
            const isOpen = accountToggle.getAttribute("aria-expanded") === "true";
            if (event.detail === 0 || lastPointerType !== "mouse") {
                setAccountMenuOpen(!isOpen);
            } else {
                setAccountMenuOpen(true);
            }
        });

        accountMenu.addEventListener("focusout", (event) => {
            if (!accountMenu.contains(event.relatedTarget)) {
                closeAccountMenu();
                lastPointerType = null;
            }
        });

        document.addEventListener("click", (event) => {
            if (!accountMenu.contains(event.target)) {
                closeAccountMenu();
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && accountToggle?.getAttribute("aria-expanded") === "true") {
            closeAccountMenu();
            accountToggle.focus();
            return;
        }
        if (event.key === "Escape" && menuToggle.getAttribute("aria-expanded") === "true") {
            closeMenu();
            menuToggle.focus();
        }
    });

    window.addEventListener("resize", () => {
        if (window.matchMedia("(min-width: 1201px)").matches) {
            closeMenu();
        }
    });
}
