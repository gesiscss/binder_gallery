function update_launch_urls() {
    var binder_select = $('#binder-select');
    var prev_binder_url = binder_select.attr('data-binder');
    var new_binder_url = binder_select.prop('value');

    $('.launch-badge-link').each(function () {
        var href = $(this).attr('href');
        $(this).attr('href', href.replace(prev_binder_url, new_binder_url));
    });

    // save latest binder url in select element
    binder_select.attr('data-binder', new_binder_url);
}

function update_binder_data() {
    // update content of popover with versions info of each selected binder
    $("#binder-versions-info").data('bs.popover').options.content = $('#binder-select').find('option:selected').data('versions');

    // update launch badge urls for selected binder
    update_launch_urls();
}

$( document ).ready(function() {
    // https://getbootstrap.com/docs/3.3/javascript/#popovers-options
    // initialize popover without content
    $("#binder-versions-info").popover({'trigger': 'hover'});

    // update data with last saved selection
    update_binder_data();

    // add event to update binder launch urls and version info when selection changes
    $('#binder-select').change(function() {
        $.ajax({
          method: "POST",
          url: "/select_binder/",
          contentType: 'application/json;charset=UTF-8',
          data: JSON.stringify({ name: $('#binder-select').find('option:selected').data('name') })
        })
          .done(function(msg) {
            console.log(msg);
            update_binder_data();
          }
          );
    });
});
