class ModalItem{
  constructor(type, title, name, extraInfo = null, imageURL = null, description = null, targetRender = null, btnAddTitle = "Adicionar"){
    this.type = type;
    this.title = title;
    this.name = name;
    this.extraInfo = extraInfo;
    this.btnAddTitle = btnAddTitle;
    this.baseClass = 'component_modal_item';
    this.imageURL = imageURL;
    this.description = description;
    this.targetRender = targetRender;
    this.instanceHash = (Math.random() + 1).toString(36).substring(4);
  }

  build(){
    $(this.targetRender).html(this.getRender());

    const thisClass = this;
    $(document).on('keyup', `.${thisClass.instanceHash} .${thisClass.baseClass}_search_item`, function (){
      let value = $(this).val();
      $(`.${thisClass.instanceHash} .component_list_items_item`).each(function() {
        let txtelen_x = $(this).text();
        try {
          txtelen_x = txtelen_x.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        } catch (error_ueueb) {}

        if (txtelen_x.search(new RegExp(value, "i")) > -1) {
          $(this).show();
        }
        else {
          $(this).hide();
        }
      }); 
    });
  }

  getRender(){
    let iosBrowser = "";
    let ua = navigator.userAgent.toLowerCase();
    if (ua.indexOf("iphone") > -1) {
      iosBrowser = " ios_browser ";
    }

    return `
        <div class="headModalItem ${this.instanceHash}">
          <div class="hideModal">
            <i class="material-icons">expand_more</i>
          </div>
          <h4 class="itemName">${this.title}</h4>
        </div>
        <div class="contentModalItem ${this.instanceHash} ${iosBrowser}">
          ${this.type != "modalFlavors" ? "" : `<div><input type='text' class='${this.baseClass}_search_item' placeholder='Pesquisar sabor...'/></div>`}
          ${this.imageURL ? this.getImageDescription() : this.getNameDescription()}
          ${this.getExtraInfo()}
        </div>
        <div class="footerModalItem ${this.instanceHash}">
          <div class="buttonsQuantity">
            <div class="${this.baseClass}_btn_quantity_card">
              <span class="${this.baseClass}_quantity_decrease ${this.type}_quantity_decrease">-</span>
              <input class="${this.baseClass}_quantity_value inteiro ${this.type}_quantity_value" value="1" type="number" maxlength='4'>
              <span class="${this.baseClass}_quantity_increase ${this.type}_quantity_increase">+</span>
            </div>
          </div>
          <div class="btnAddModalItem ${this.type}_btnAddModalItem">
            <span>${this.btnAddTitle}</span>
            <span id="${this.type}_price">R$ 0,00</span>
          </div>
        </div>
    `;
  }

  getExtraInfo(){
    if (this.extraInfo == null) return "";

    return `
      <div class="${this.baseClass}_extraInfo">
        ${this.extraInfo}
      </div>
    `;
  }

  getImageDescription(){
    if (this.imageURL == null) return "";

    return `
      <div class="${this.baseClass}_div_image">
        <div class="${this.baseClass}_image">
          <img src="${this.imageURL}" />
          </div>
          ${this.getNameDescription()}
      </div>
    `;
  }

  getNameDescription(){
    return `
      <div class="${this.baseClass}_name_description">
        ${!this.name ? "" :
        `<div class="${this.baseClass}_name">${this.name}</div>`
        }
        ${!this.description ? "" :
        `<div class="${this.baseClass}_description">${this.description}</div>`
        }
      </div>
    `;
  }
}