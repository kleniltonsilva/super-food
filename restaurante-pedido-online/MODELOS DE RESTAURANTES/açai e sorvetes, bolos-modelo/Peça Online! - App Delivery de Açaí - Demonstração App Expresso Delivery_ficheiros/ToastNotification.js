class ToastNotification{
  constructor(elementId, type, title, message, slider = false, showClose = true, callBackClose = null){
    this.elementId = elementId;
    this.type = type ?? "info",
    this.title = title;
    this.message = message;
    this.slider = slider;
    this.showClose = showClose;
    this.callBackClose = callBackClose;
    this.instanceHash = (Math.random() + 1).toString(36).substring(4);
  }

  getRender(){
    const thisInstance = this;
    if (this.showClose) {
      $(document).on('click', `.${this.instanceHash} .toast-notification-close i`, function(){
        if (thisInstance.callBackClose != null) {
          thisInstance.callBackClose();
        }
        $(this).closest(".toast-notification").remove();
      })
    }

    return `
      <div class="${this.instanceHash} toast-notification toast-notification-type-${this.type} ${this.slider ? "toast-notification-slider" : ""}" id="${this.elementId}">
        <div class="toast-notification-icon">
          <i class="material-icons">info</i>
        </div>
        <div class="toast-notification-body">
          <p class="toast-notification-title">${this.title}</p>
          ${this.message ? `<p class="toast-notification-message">${this.message}</p>` : ""}
        </div>
        <div class="toast-notification-close">
          ${this.showClose ? `<i class="material-icons">close</i>` : ""}
        </div>
      </div>
    `
  }
}