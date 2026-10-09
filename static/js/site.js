(() => {
  const nav = document.getElementById("site-nav");
  if (nav) {
    const update = () => { nav.dataset.solid = String(window.scrollY > 40); };
    update();
    window.addEventListener("scroll", update, { passive: true });
  }

  const explorer = document.querySelector("[data-destinations]");
  if (explorer) {
    const items = [...explorer.querySelectorAll("[data-destination]")];
    const image = explorer.querySelector("[data-destination-image]");
    const city = explorer.querySelector("[data-destination-city]");
    const region = explorer.querySelector("[data-destination-region]");
    const activate = (item) => {
      items.forEach((i) => { i.dataset.active = String(i === item); });
      if (image) image.style.objectPosition = item.dataset.position;
      if (city) city.textContent = item.dataset.city;
      if (region) region.textContent = item.dataset.region;
    };
    items.forEach((item) => {
      item.addEventListener("mouseenter", () => activate(item));
      item.addEventListener("focusin", () => activate(item));
    });
  }
})();
