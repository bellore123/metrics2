document.addEventListener("DOMContentLoaded", function () {
    const googleButton = document.getElementById(
        "studentGoogleButton"
    );

    if (googleButton) {
        googleButton.addEventListener("click", function () {
            googleButton.classList.add("is-loading");
        });
    }

    const loginCard = document.querySelector(
        ".student-login-card"
    );

    const visualPanel = document.querySelector(
        ".student-visual-panel"
    );

    if (
        loginCard &&
        visualPanel &&
        window.matchMedia("(pointer: fine)").matches
    ) {
        document.addEventListener(
            "mousemove",
            function (event) {
                const x =
                    event.clientX / window.innerWidth - 0.5;

                const y =
                    event.clientY / window.innerHeight - 0.5;

                loginCard.style.transform =
                    `translate3d(${x * 5}px, ${y * 5}px, 0)`;

                visualPanel.style.backgroundPosition =
                    `${50 + x * 3}% ${50 + y * 3}%`;
            }
        );

        document.addEventListener(
            "mouseleave",
            function () {
                loginCard.style.transform =
                    "translate3d(0, 0, 0)";
            }
        );
    }

    const messages = document.querySelectorAll(
        ".student-message"
    );

    messages.forEach(function (message) {
        setTimeout(function () {
            message.style.opacity = "0";
            message.style.transform =
                "translateY(-8px)";

            setTimeout(function () {
                message.remove();
            }, 350);
        }, 5000);
    });
});