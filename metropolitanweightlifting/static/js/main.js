var WIDTH_LIMIT = 700;


$(function() {

    /**
     * Sidebar animation / functionality
     */
    $('.sidebar li').hover(
        function() {
            $('.active').removeClass('active').addClass('activate');
        },
        function() {
            $('.activate').removeClass('activate').addClass('active');
        }
    );
    $('.active').children().click(function(e) {
        e.preventDefault();
    });

    /**
     * Calendar toggle
     */
    $('#calendar-tab').click(
        function() {
            $('.calendar').slideToggle("fast", function() {
                var calendar_iframe = $('iframe', this);
                if (!calendar_iframe.attr('src')) {
                    calendar_iframe.attr('src', "https://www.google.com/calendar/embed?src=metropolitanweightlifting%40gmail.com&ctz=America/New_York");
                }
            });
        }
    );

    /**
     * Window width dependent changes
     */
    windowWidthChanges();
    $(window).resize(function() {
        windowWidthChanges();
    });

    /**
     * Add Athlete Bio Form toggles
     */
    var gender = $('#gender');
    weightClassSwitch(gender.val());
    gender.click(function() {
        weightClassSwitch(gender.val());
    });

    /**
     * Meet Filter auto-submission
     */
    $('#meets-filter').on("change", function() {
        $(this).submit();
    });

    /**
     * Results Filter Form actions
     */
    // auto-submission
    var resultsFilter = $('#results-filter');
    resultsFilter.on("change", function() {
        $(this).submit();
    });
    // reset Weight Class to 'all' on Gender change
    resultsFilter.find('#gender').on("change", function() {
        resultsFilter.find('#weight_class').val('all')
    });

    /**
     * Article Admin Form
     */
    var articleType = $('#type');
    articleTypeSwitch(articleType.val());
    articleType.click(function() {
        articleTypeSwitch(articleType.val());
    });

    var images = $('#images');
    var wrapText = $('#wrap_text').parent();
    var imgCaptions = $('#img_captions');
    var imgCaption = $('#img_caption_0').parent();
    var existingImgCaptions = $("label[for^='img_existing_caption']");
    wrapText.hide();
    if (existingImgCaptions.length == 1) {
        wrapText.show();
    }
    imgCaption.hide();
    images.on("change", function() {
        var files = $(this).prop("files");
        imgCaption.show();
        if (files.length > 1) {
            wrapText.hide();
            imgCaption.find("label").text("Caption for '" + files[0].name + "'");
            for (var i = 1; i < files.length; i++) {
                var clone = imgCaption.clone();
                var clone_label = clone.find("label");
                var clone_input = clone.find("input");
                var clone_identifier = "img_caption_" + i;
                clone_label.text("Caption for '" + files[i].name + "'");
                clone_label.attr("for", clone_identifier);
                clone_input.attr("id", clone_identifier);
                clone_input.attr("name", clone_identifier);
                imgCaptions.append(clone);
            }
        }
        else {
            if (existingImgCaptions.length == 0) {
                wrapText.show();
            }
            imgCaption.find("label").text("Caption");
            imgCaptions.children().not(imgCaption).remove();
        }
    });

    /**
     * Slick (image-carousel)
     */
    $('.image-carousel').on('init', function(slick) {
        $('.image_caption').text($('.slick-active .article-image').data("caption"))
    }).on('beforeChange', function (slick, currentSlide, nextSlide) {
        $('.image_caption').fadeOut('fast', function() {
            $(this).text($('.slick-active .article-image').data("caption"));
            $(this).fadeIn('fast');
        });
    }).slick({
        dots: false,
        infinite: true,
        speed: 500,
        slidesToShow: 1
    });

    /**
     * Image overlay
     */
    $('img.to-fullsize').click(
        function() {
            var img = $('<img>');
            img.attr('src', $(this).attr('src'));

            var overlayItem = $('.overlay-item');
            overlayItem.append(img);
            $('.overlay').fadeIn('fast');
            overlayItem.fadeIn('fast');

            $('body').css('overflow', 'hidden');
        }
    );
    $('.overlay, .overlay-item').click(function() {
        $('.overlay').fadeOut('fast');
        $('.overlay-item').fadeOut('fast', function() {
            $(this).children().remove();
        });
        $('body').css('overflow', 'auto');
    });

    /**
     * Athlete bio toggle by target
     */
    if (window.location.hash && window.location.pathname === "/bios") {
        toggleAthleteDetails(window.location.hash.substring(1));
    }

});

function dropdownMenu() {
    if ($(window).width() < WIDTH_LIMIT) {
        $('.dropdown-menu').slideToggle('fast');
    }
}

function windowWidthChanges() {
    $('.dropdown-menu').hide();
}

function articleTypeSwitch(articleTypeValue) {
    var images = $('#images').parent();
    var video_src = $('#video_src').parents('.full-width');
    var pdf = $('#pdf').parents('.full-width');
    switch(articleTypeValue) {
        case 'text_only':
            images.hide();
            video_src.hide();
            pdf.hide();
            break;
        case 'images':
            images.show();
            video_src.hide();
            pdf.hide();
            break;
        case 'video':
            video_src.show();
            images.hide();
            pdf.hide();
            break;
        case 'pdf':
            pdf.show();
            images.hide();
            video_src.hide();
    }
}

function weightClassSwitch(genderValue) {
    var li_wc_male_label = $('label[for="weight_class_male"]');
    var li_wc_male_select = $('#weight_class_male').parent();
    var li_wc_female_label = $('label[for="weight_class_female"]');
    var li_wc_female_select = $('#weight_class_female').parent();
    switch(genderValue) {
        case "m":
            li_wc_male_label.css('display', 'inline');
            li_wc_male_select.css('display', 'inline');
            li_wc_female_label.css('display', 'none');
            li_wc_female_select.css('display', 'none');
        break;
        case "f":
            li_wc_female_label.css('display', 'inline');
            li_wc_female_select.css('display', 'inline');
            li_wc_male_label.css('display', 'none');
            li_wc_male_select.css('display', 'none');
        break;
    }
}

function deleteArticleImage(src, id, button) {
    if (confirm("Delete article image '" + src + "'?") === true) {
        button.form.article_image_id.value = id;
        button.form.submit();
    }
}

function deleteAthlete(name, id, button) {
    if (confirm("Delete athlete bio for " + name + "?") === true) {
        button.form.athlete_id.value = id;
        button.form.submit();
    }
}

function deleteArticle(title, id, button) {
    if (confirm("Delete article '" + title + "'?") === true) {
        button.form.article_id.value = id;
        button.form.submit();
    }
}

function deleteMeet(name, id, button) {
    if (confirm("Delete meet '" + name + "'?") === true) {
        console.log(button.form);
        button.form.meet_id.value = id;
        button.form.submit()
    }
}

function toggleAthleteDetails(id) {
    var id_image = $('#' + id + '_image');
    var id_details = $('#' + id + '_details');
    $('.athlete-thumbnail').not(id_image).show();
    $('.roster-details').not(id_details).hide();
    id_image.toggle();
    id_details.toggle();
}