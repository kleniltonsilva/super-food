$(document).ready(function(e){
  $(document).on('click', ".hideModal", function(e) {
    let modalTarget = "#";
    if ($(this).parent().parent().hasClass('component_editor_pizza_modalEddy')) {
      modalTarget = ".component_editor_pizza_";
    }

    if ($(this).parent().parent().hasClass('component_editor_generic_modalEddy')) {
      modalTarget = ".component_editor_generic_";
    }
    
    closeModalEddy(modalTarget);
  });

  $(document).on('click', ".backdrop", function(e) {
    let modalTarget = "#";
    if ($(this).hasClass('component_editor_pizza_backdrop')) {
      modalTarget = ".component_editor_pizza_";
    }

    if ($(this).hasClass('component_editor_generic_backdrop')) {
      modalTarget = ".component_editor_generic_";
    }

    closeModalEddy(modalTarget);
  });
})

function openModalEddy(modalTarget = "#"){
  const backdropTarget = modalTarget == "#" ? "." : modalTarget;
  $(`${modalTarget}modalEddy`).addClass('modal');
  $(`${modalTarget}modalEddy`).addClass('fade');
  $(`${backdropTarget}backdrop`).show();
  $(`${modalTarget}modalEddy`).show();
}

function closeModalEddy(modalTarget = "#"){
  const backdropTarget = modalTarget == "#" ? "." : modalTarget;
  $(`${modalTarget}modalEddy`).html('');
  $(`${backdropTarget}backdrop`).css('z-index', 9997);
  $(`${modalTarget}modalEddy`).css('z-index', 9998);
  $(`${backdropTarget}backdrop`).hide();
  $(`${modalTarget}modalEddy`).hide();
  if (typeof quantityIncrementCurrent != 'undefined') quantityIncrementCurrent = 1;
  if (typeof itemPriceCurrent != 'undefined' && $('.modalAddItem_btnAddModalItem').is(":visible")) itemPriceCurrent = 0;
  if (typeof dataItemCurrent != 'undefined') dataItemCurrent = null;
  $('#modalEddy').attr('class').split(/\s+/).map(x => {
    modalTarget = modalTarget.replace('.', '');
    if (x != 'modalEddy' && x != `${modalTarget}modalEddy`) {
      $(`${modalTarget}modalEddy`).removeClass(x);
    } else if (modalTarget != "#") {
      Array.from($(`.${modalTarget}modalEddy`)[0].classList).map(c => {
        if (c != `${modalTarget}modalEddy` && c != "modalEddy"  && c != "modal" && c.indexOf("modal") > -1) {
          $(`.${modalTarget}modalEddy`).removeClass(c);
        }
      })
    }
  })
}

function setDataModalEddy(html){
  $('#modalEddy').html(html);
}