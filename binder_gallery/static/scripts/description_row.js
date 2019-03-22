// https://datatables.net/examples/api/row_details.html
$(document).ready(function () {
    // Add event listener for opening and closing description row
    $('tbody').on('click', 'tr', function () {
        var description = $(this).data().description;
        //console.log(description);

        if ($(this).hasClass('shown') && $(this).next('tr').hasClass('description_row')) {
            // remove description row
            $(this).removeClass('shown');
            $(this).next('tr.description_row').remove();
        }
        else if (description) {
            // add description row
            $(this).addClass('shown');
            var description_row = '<tr class="description_row"><td colspan="' + $(this).find('td').length +
                                  '" style="padding-left:25px;">' +
                                  description +
                                  '</td></tr>';
            $(this).after(description_row);
        }
        // don't return anything to allow default behaviours, such as link click
        // return false;
    });
});
