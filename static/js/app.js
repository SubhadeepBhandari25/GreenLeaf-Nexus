// GreenLeaf Nexus Global JavaScript
document.addEventListener("DOMContentLoaded", () => {
  // Mobile Sidebar Toggle
  const sidebarToggle = document.getElementById("sidebarToggle");
  const appSidebar = document.getElementById("appSidebar");

  if (sidebarToggle && appSidebar) {
    sidebarToggle.addEventListener("click", () => {
      appSidebar.classList.toggle("show");
    });

    // Close when clicking outside on mobile
    document.addEventListener("click", (e) => {
      if (
        window.innerWidth < 992 &&
        appSidebar.classList.contains("show") &&
        !appSidebar.contains(e.target) &&
        !sidebarToggle.contains(e.target)
      ) {
        appSidebar.classList.remove("show");
      }
    });
  }

  // Auto-dismiss standard alerts after 5 seconds
  const autoAlerts = document.querySelectorAll(".alert.alert-success, .alert.alert-info");
  autoAlerts.forEach((alert) => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 5000);
  });
});

// CSRF Token Helper for AJAX
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
}
