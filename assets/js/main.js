document.addEventListener("DOMContentLoaded", () => {
    /* ================= Desktop Dropdown ================= */
    const dropdownItems = document.querySelectorAll(".nav__item--has-dropdown");

    dropdownItems.forEach((item) => {
        const link = item.querySelector(".nav__link");
        const arrow = item.querySelector(".arrow");

        link?.addEventListener("click", (e) => {
            e.preventDefault();
            item.classList.toggle("open");
            if (arrow) arrow.classList.toggle("rotate");
        });
    });

    document.addEventListener("click", (e) => {
        if (!e.target.closest(".nav__item--has-dropdown")) {
           
            
            dropdownItems.forEach((item) => {
                
                item.classList.remove("open");
                const arrow = item.querySelector(".arrow");
                if (arrow) arrow.classList.remove("rotate");
            });
        }
    });

    /* ================= Mobile Menu ================= */
    const burgerBtn = document.getElementById("burgerBtn");
    const mobileNav = document.getElementById("mobileNav");

    function openMobileNav() {
        mobileNav.classList.toggle("active");
        burgerBtn.classList.toggle("active");
        document.body.style.overflow =
            document.body.style.overflow === 'hidden' ? '' : 'hidden';
    }


    burgerBtn?.addEventListener("click", openMobileNav);

    document.addEventListener("click", (e) => {
        if (mobileNav.classList.contains("active")) {
            if (
                !e.target.closest(".mobile-nav__panel") &&
                !e.target.closest("#burgerBtn")
            ) {
                openMobileNav();
            }
        }
    });

    /* ================= Mobile Submenu Toggle ================= */
    document.querySelectorAll(".mobile-submenu-toggle").forEach((toggle) => {
        toggle.addEventListener("click", function () {
            const parent = this.closest(".mobile-has-submenu");
            if (!parent) return;

            const submenu = parent.querySelector(".mobile-submenu");
            const isOpen = parent.classList.contains("open");

            if (isOpen) {
                // Закрытие с анимацией
                submenu.style.maxHeight = submenu.scrollHeight + 'px';

                // Запускаем рефлоу для анимации
                submenu.offsetHeight;

                submenu.style.maxHeight = '0';
                submenu.style.opacity = '0';
                submenu.style.transform = 'translateY(-10px)';

                // Ждем завершения анимации перед скрытием
                setTimeout(() => {
                    submenu.setAttribute("hidden", "");
                    parent.classList.remove("open");
                }, 300);

                this.setAttribute("aria-expanded", "false");
            } else {
                // Открытие с анимацией
                submenu.removeAttribute("hidden");

                // Устанавливаем начальные значения
                submenu.style.maxHeight = '0';
                submenu.style.opacity = '0';
                submenu.style.transform = 'translateY(-10px)';

                // Запускаем рефлоу
                submenu.offsetHeight;

                // Анимируем к полной высоте
                submenu.style.maxHeight = submenu.scrollHeight + 'px';
                submenu.style.opacity = '1';
                submenu.style.transform = 'translateY(0)';

                parent.classList.add("open");
                this.setAttribute("aria-expanded", "true");

                // Убираем фиксированную высоту после анимации
                setTimeout(() => {
                    if (submenu.style.maxHeight !== '0px') {
                        submenu.style.maxHeight = 'none';
                    }
                }, 300);
            }
        });
    });
    /* ================= Scroll to Top Button ================= */
    const pointer = document.getElementById("pointer");
    const pointerBtn = document.querySelector(".pointer_btn");

    if (pointer) {
        pointer.style.opacity = "0";
        pointer.style.visibility = "hidden";
    }

    pointerBtn?.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    window.addEventListener("scroll", () => {
        if (!pointer) return;
        if (window.scrollY > 300) {
            pointer.style.opacity = "1";
            pointer.style.visibility = "visible";
        } else {
            pointer.style.opacity = "0";
            pointer.style.visibility = "hidden";
        }
    });
});

document.addEventListener("DOMContentLoaded", () => {
    const searchSelect = document.getElementById("searchSelect");
    const searchBtn = document.getElementById("searchSelectBtn");

    if (!searchSelect || !searchBtn) return;

    const options = searchSelect.querySelectorAll(".search-select__option");
    const arrow = searchBtn.querySelector(".search-select__arrow");


    searchBtn.addEventListener("click", (e) => {
        e.preventDefault();
        searchSelect.classList.toggle("open");
    });

    options.forEach((option) => {
        option.addEventListener("click", () => {
            const label = searchSelect.querySelector(".search-select__label");
            label.textContent = option.textContent;
            searchSelect.classList.remove("open");
        });
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
        if (!searchSelect.contains(e.target)) {
            searchSelect.classList.remove("open");
        }
    });
});

// flags
document.addEventListener("DOMContentLoaded", function () {
    const lastFlag = document.querySelector(".last-flag");
    const toggleBtn = document.getElementById("toggleFlag");
    if (!lastFlag || !toggleBtn) return;
    function updateFlags() {
        if (window.innerWidth <= 768) {
            if (lastFlag) lastFlag.style.display = "none";
            toggleBtn.addEventListener("click", toggleLastFlag);
        } else {
            if (lastFlag) lastFlag.style.display = "flex";
            toggleBtn.removeEventListener("click", toggleLastFlag);
        }
    }

    function toggleLastFlag() {
        if (lastFlag.style.display === "none") {
            lastFlag.style.display = "flex";
        } else {
            lastFlag.style.display = "none";
        }
    }

    updateFlags();
    window.addEventListener("resize", updateFlags);
});


//Adupdate text
document.addEventListener("DOMContentLoaded", function () {
    const textBlocks = document.querySelectorAll("#adupdate .adupdate__text");

    textBlocks.forEach((block) => {
        const textElement = block.querySelector("span");
        const toggleBtn = block.querySelector(".more span");
        const arrow = block.querySelector(".more img");
        if (!textElement || !toggleBtn) return;

        if (arrow) arrow.style.transition = "transform 0.3s ease";

        const fullText = textElement.textContent.trim();
        const words = fullText.split(" ");
        const shortText = words.slice(0, 70).join(" ") + "...";
        textElement.textContent = shortText;

        let expanded = false;
        let isAnimating = false;

        toggleBtn.addEventListener("click", () => {
            if (isAnimating) return;
            isAnimating = true;

            const container = textElement.parentElement;
            const startHeight = container.scrollHeight;

            textElement.textContent = expanded ? shortText : fullText;

            requestAnimationFrame(() => {
                const endHeight = container.scrollHeight;
                container.style.height = startHeight + "px";
                container.offsetHeight;

                container.style.transition = "height 0.4s ease";
                container.style.height = endHeight + "px";

                container.addEventListener("transitionend", function handler() {
                    container.style.height = "auto";
                    container.style.transition = "";
                    container.removeEventListener("transitionend", handler);
                    isAnimating = false;
                });

                expanded = !expanded;
                toggleBtn.textContent = expanded ? "Свернуть" : "Развернуть";

                if (arrow)
                    arrow.style.transform = expanded ? "rotate(180deg)" : "rotate(0deg)";
            });
        });
    });
});

// Category
// document.addEventListener("DOMContentLoaded", function () {
//     const categoryBox = document.querySelector("#category .category__box");
//     const items = categoryBox.querySelectorAll(".item");
//     const toggleBtn = document.querySelector("#category .category__toggle span");
//     const toggleIcon = document.querySelector(
//         "#category .category__toggle .toggle-icon"
//     );

//     const visibleCount = 10;
//     let expanded = false;

//     items.forEach((item, index) => {
//         if (index >= visibleCount) item.style.display = "none";
//     });

//     toggleBtn.addEventListener("click", () => {
//         expanded = !expanded;

//         if (expanded) {
//             items.forEach((item) => (item.style.display = "flex"));
//             toggleBtn.textContent = "Свернуть";
//             toggleIcon.style.transform = "rotate(180deg)";
//         } else {
//             items.forEach((item, index) => {
//                 item.style.display = index < visibleCount ? "flex" : "none";
//             });
//             toggleBtn.textContent = "Развернуть";
//             toggleIcon.style.transform = "rotate(0deg)";
//         }
//     });
// });

// // Tips carousel
// const track = document.querySelector(".carousel__track");
// const items = document.querySelectorAll(".carousel__item");
// const dotsContainer = document.querySelector(".carousel__dots");

// const itemsPerSlide = 3;
// const totalSlides = Math.ceil(items.length / itemsPerSlide);

// let currentSlide = 0;

// // Generate dots
// for (let i = 0; i < totalSlides; i++) {
//     const dot = document.createElement("div");
//     dot.classList.add("carousel__dot");
//     if (i === 0) dot.classList.add("active");
//     dot.addEventListener("click", () => goToSlide(i));
//     dotsContainer.appendChild(dot);
// }

// function goToSlide(slideIndex) {
//     currentSlide = slideIndex;
//     const offset = -(100 * slideIndex);
//     track.style.transform = `translateX(${offset}%)`;

//     document.querySelectorAll(".carousel__dot").forEach((dot, idx) => {
//         dot.classList.toggle("active", idx === slideIndex);
//     });
// }

/* ============================== Category page ============================== */

// Category Search
document.addEventListener("DOMContentLoaded", () => {
    const dropdowns = document.querySelectorAll(".dropdown");

    dropdowns.forEach((dropdown) => {
        const toggle = dropdown.querySelector(".dropdown__control");
        const menu = dropdown.querySelector(".dropdown__menu");
        const label = dropdown.querySelector(".selectedText");
        const items = dropdown.querySelectorAll(".dropdown__item");

        function openDropdown() {
            closeAllDropdowns();
            dropdown.classList.add("dropdown--open");
            toggle.setAttribute("aria-expanded", "true");
            items[0].focus();
        }

        function closeDropdown() {
            dropdown.classList.remove("dropdown--open");
            toggle.setAttribute("aria-expanded", "false");
        }

        function toggleDropdown() {
            if (dropdown.classList.contains("dropdown--open")) closeDropdown();
            else openDropdown();
        }

        toggle.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleDropdown();
        });

        items.forEach((item) => {
            item.addEventListener("click", () => {
                label.textContent = item.textContent.trim();
                closeDropdown();
            });

            item.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    item.click();
                } else if (e.key === "ArrowDown") {
                    e.preventDefault();
                    const next = item.nextElementSibling;
                    if (next) next.focus();
                } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    const prev = item.previousElementSibling;
                    if (prev) prev.focus();
                } else if (e.key === "Escape") {
                    closeDropdown();
                    toggle.focus();
                }
            });
        });

        document.addEventListener("click", (e) => {
            if (!dropdown.contains(e.target)) {
                closeDropdown();
            }
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") closeDropdown();
        });
    });

    function closeAllDropdowns() {
        document.querySelectorAll(".dropdown.dropdown--open").forEach((open) => {
            open.classList.remove("dropdown--open");
            const toggle = open.querySelector(".dropdown__control");
            if (toggle) toggle.setAttribute("aria-expanded", "false");
        });
    }
});

// Category box
// document.addEventListener("DOMContentLoaded", function () {
//     const categoryBox = document.querySelector("#category .category__box");
//     const items = categoryBox.querySelectorAll(".item");
//     const toggleBtn = document.querySelector("#category .category__toggle span");
//     const toggleIcon = document.querySelector(
//         "#category .category__toggle .toggle-icon"
//     );

//     const visibleCount = 10;
//     let expanded = false;

//     items.forEach((item, index) => {
//         if (index >= visibleCount) item.style.display = "none";
//     });

//     toggleBtn.addEventListener("click", () => {
//         expanded = !expanded;

//         if (expanded) {
//             items.forEach((item) => (item.style.display = "flex"));
//             toggleBtn.textContent = "Свернуть";
//             toggleIcon.style.transform = "rotate(180deg)";
//         } else {
//             items.forEach((item, index) => {
//                 item.style.display = index < visibleCount ? "flex" : "none";
//             });
//             toggleBtn.textContent = "Развернуть";
//             toggleIcon.style.transform = "rotate(0deg)";
//         }
//     });
// });

// Menu active
document.addEventListener("DOMContentLoaded", function () {
    const menuItems = document.querySelectorAll(".menu_list .item");

    menuItems.forEach((item) => {
        item.addEventListener("click", function () {
            menuItems.forEach((btn) => btn.classList.remove("active"));
            this.classList.add("active");
        });
    });
});

// Range - нужно обернуть в DOMContentLoaded и добавить проверки
document.addEventListener("DOMContentLoaded", function () {
    const rangeMin = document.getElementById("rangeMin");
    const rangeMax = document.getElementById("rangeMax");
    const progress = document.querySelector(".progress");
    const minVal = document.getElementById("minVal");
    const maxVal = document.getElementById("maxVal");

    // Если элементов нет - выходим
    if (!rangeMin || !rangeMax || !progress || !minVal || !maxVal) return;

    const gap = 1000;

    function updateProgress() {
        let min = parseInt(rangeMin.value);
        let max = parseInt(rangeMax.value);

        if (max - min < gap) {
            if (event.target === rangeMin) {
                rangeMin.value = max - gap;
            } else {
                rangeMax.value = min + gap;
            }
            min = parseInt(rangeMin.value);
            max = parseInt(rangeMax.value);
        }

        const percentMin = (min / rangeMin.max) * 100;
        const percentMax = (max / rangeMax.max) * 100;

        progress.style.left = percentMin + "%";
        progress.style.right = (100 - percentMax) + "%";

        minVal.value = min;
        maxVal.value = max;
    }

    function updateFromInputs() {
        let min = parseInt(minVal.value);
        let max = parseInt(maxVal.value);

        if (isNaN(min)) min = 0;
        if (isNaN(max)) max = 100000;

        if (max - min < gap) {
            if (event.target === minVal) {
                min = max - gap;
            } else {
                max = min + gap;
            }
        }

        if (min < 0) min = 0;
        if (max > 100000) max = 100000;

        rangeMin.value = min;
        rangeMax.value = max;

        updateProgress();
    }

    rangeMin.addEventListener("input", updateProgress);
    rangeMax.addEventListener("input", updateProgress);
    minVal.addEventListener("input", updateFromInputs);
    maxVal.addEventListener("input", updateFromInputs);

    updateProgress();
});

// rangeMin.addEventListener("input", updateProgress);
// rangeMax.addEventListener("input", updateProgress);
// minVal.addEventListener("input", updateFromInputs);
// maxVal.addEventListener("input", updateFromInputs);

// updateProgress();

// ==============================================
document.addEventListener("DOMContentLoaded", () => {
    const gridBtn = document.querySelector(".header_filter .btn:nth-of-type(1)");
    const listBtn = document.querySelector(".header_filter .btn:nth-of-type(2)");
    const barsBtn = document.querySelector(".header_filter .btn:nth-of-type(3)");

    // ДОБАВИТЬ ПРОВЕРКУ ДЛЯ ВСЕХ КНОПОК
    if (!gridBtn || !listBtn || !barsBtn) return;

    const allBtns = [gridBtn, listBtn, barsBtn];

    const periodTitles = document.querySelectorAll(".period__title");
    const carousels = document.querySelectorAll(".stage-padding-carousel");
    const adupdateButtons = document.querySelectorAll(".adupdate__buttons");
    const listviewMains = document.querySelectorAll(".listview_main");
    const listImgs = document.querySelectorAll(".list__img");
    const owners = document.querySelectorAll(".owner");

    function resetAll() {
        periodTitles.forEach((el) => (el.style.display = "none"));
        carousels.forEach((el) => (el.style.display = "none"));
        adupdateButtons.forEach((el) =>
            el.style.setProperty("display", "none", "important")
        );
        listviewMains.forEach((el) => {
            el.classList.remove("owner");
            el.style.display = "none";
        });
        listImgs.forEach((el) => (el.style.display = ""));
    }

    function setActive(btn) {
        allBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
    }

    gridBtn.addEventListener("click", () => {
        setActive(gridBtn);
        resetAll();

        periodTitles.forEach((el) => (el.style.display = "block"));
        carousels.forEach((el) => (el.style.display = "block"));
        adupdateButtons.forEach((el) =>
            el.style.setProperty("display", "flex", "important")
        );
        listviewMains.forEach((el) => {
            el.classList.remove("owner");
            el.style.display = "none";
        });
    });

    listBtn.addEventListener("click", () => {
        setActive(listBtn);
        resetAll();

        periodTitles.forEach((el) => (el.style.display = "none"));
        carousels.forEach((el) => (el.style.display = "none"));
        adupdateButtons.forEach((el) =>
            el.style.setProperty("display", "none", "important")
        );
        listviewMains.forEach((el) => (el.style.display = "block"));
    });

    barsBtn.addEventListener("click", () => {
        setActive(barsBtn);
        resetAll();

        listImgs.forEach((img) => (img.style.display = "none"));

        owners.forEach((owner) => {
            const existing = owner.querySelector(".studio-text");
            if (!existing) {
                const span = document.createElement("span");
                span.classList.add("studio-text");
                span.textContent = " Сдам в аренду студия";
                owner.appendChild(span);
            }
        });

        listviewMains.forEach((el) => {
            el.classList.add("owner");
            el.style.display = "block";
        });
    });

    gridBtn.click();
});
