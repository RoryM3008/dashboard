/**
 * Click-to-chart: clicking any element with class "clickable-ticker"
 * and a data-ticker attribute sets the chart-ticker-input value.
 */
document.addEventListener("click", function (e) {
    var el = e.target.closest(".clickable-ticker");
    if (!el) return;
    var ticker = el.getAttribute("data-ticker");
    if (!ticker) return;
    var input = document.getElementById("chart-ticker-input");
    if (!input) return;
    // Set value via React's internal setter so Dash picks up the change
    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, "value"
    ).set;
    nativeInputValueSetter.call(input, ticker);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    // Also trigger change for debounced inputs
    input.dispatchEvent(new Event("change", { bubbles: true }));
});
