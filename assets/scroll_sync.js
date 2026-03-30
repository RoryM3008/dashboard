/* Sync the top horizontal scrollbar with the prices table scroll */
(function () {
    var syncing = false;

    function setup() {
        var top = document.getElementById("prices-top-scroll");
        var bot = document.getElementById("prices-table-inner");
        if (!top || !bot) return;

        /* Make the top scrollbar div match the table's scroll width */
        var spacer = top.firstElementChild;
        if (spacer) spacer.style.width = bot.scrollWidth + "px";

        top.onscroll = function () {
            if (syncing) return;
            syncing = true;
            bot.scrollLeft = top.scrollLeft;
            syncing = false;
        };
        bot.onscroll = function () {
            if (syncing) return;
            syncing = true;
            top.scrollLeft = bot.scrollLeft;
            syncing = false;
        };
    }

    /* Re-run setup whenever the DOM changes (new table rendered) */
    var observer = new MutationObserver(function () { setTimeout(setup, 100); });
    observer.observe(document.body, { childList: true, subtree: true });
})();
